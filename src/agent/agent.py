import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


ACTION_PATTERN = re.compile(
    r"Action:\s*([A-Za-z_]\w*)\s*\(\s*(\{.*\})\s*\)",
    flags=re.DOTALL,
)
FINAL_PATTERN = re.compile(r"Final Answer:\s*(.+)", flags=re.DOTALL)


def parse_action(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parse `Action: tool_name({"arg": "value"})` from an LLM response."""
    match = ACTION_PATTERN.search(text)
    if match is None:
        return None

    arguments = json.loads(match.group(2))
    if not isinstance(arguments, dict):
        raise ValueError("Action arguments must be a JSON object")
    return match.group(1), arguments


def parse_final_answer(text: str) -> Optional[str]:
    """Return the text following `Final Answer:` when present."""
    match = FINAL_PATTERN.search(text)
    return match.group(1).strip() if match else None


class ReActAgent:
    """A bounded Thought-Action-Observation agent."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
    ):
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[str] = []
        self.tool_calls = 0

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(
            (
                f"- {tool['name']}: {tool['description']} "
                f"Parameters: {json.dumps(tool.get('parameters', {}))}"
            )
            for tool in self.tools
        )
        return f"""
You are an e-commerce ReAct agent.

Available tools:
{tool_descriptions}

Rules:
1. Use only a tool listed above. Never invent a tool.
2. Respond with exactly one Action or one Final Answer per turn.
3. Action format: Action: tool_name({{"argument": "value"}})
4. Action arguments must be valid JSON with double quotes.
5. The application executes each Action and provides its Observation.
6. Never invent an Observation.
7. Use tool evidence before stating price, stock, coupon, or shipping facts.
8. If an Observation contains an error, correct the Action or give a safe answer.

Valid response formats:
Thought: brief reason
Action: tool_name({{"argument": "value"}})

or:

Final Answer: answer grounded in the Observations
""".strip()

    def run(self, user_input: str) -> str:
        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("user_input must be a non-empty string")

        self.history = []
        self.tool_calls = 0
        logger.log_event(
            "AGENT_START",
            {"model": self.llm.model_name, "max_steps": self.max_steps},
        )

        for step in range(1, self.max_steps + 1):
            prompt = self._build_prompt(user_input)
            result = self.llm.generate(
                prompt,
                system_prompt=self.get_system_prompt(),
            )
            llm_output = result["content"].strip()
            self.history.append(llm_output)
            logger.log_event(
                "LLM_RESPONSE",
                {"step": step, "content": llm_output},
            )

            final_answer = parse_final_answer(llm_output)
            if final_answer is not None:
                logger.log_event(
                    "AGENT_END",
                    {"steps": step, "tool_calls": self.tool_calls},
                )
                return final_answer

            try:
                action = parse_action(llm_output)
            except (json.JSONDecodeError, ValueError) as exc:
                observation = {
                    "ok": False,
                    "error": "invalid_action",
                    "message": str(exc),
                }
                self._append_observation(step, observation)
                continue

            if action is None:
                observation = {
                    "ok": False,
                    "error": "unrecognized_response",
                    "message": "Expected Action or Final Answer",
                }
                self._append_observation(step, observation)
                continue

            tool_name, arguments = action
            observation = self._execute_tool(tool_name, arguments)
            self._append_observation(step, observation)

        logger.log_event(
            "AGENT_FALLBACK",
            {"steps": self.max_steps, "tool_calls": self.tool_calls},
        )
        return (
            "I could not complete the request safely within the available "
            "number of steps."
        )

    def _build_prompt(self, user_input: str) -> str:
        transcript = "\n".join(self.history)
        if transcript:
            return f"Question: {user_input.strip()}\n\n{transcript}"
        return f"Question: {user_input.strip()}"

    def _append_observation(
        self, step: int, observation: Dict[str, Any]
    ) -> None:
        observation_text = (
            "Observation: "
            + json.dumps(observation, ensure_ascii=False, sort_keys=True)
        )
        self.history.append(observation_text)
        logger.log_event(
            "OBSERVATION",
            {"step": step, "result": observation},
        )

    def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        available_tools = {
            tool["name"]: tool for tool in self.tools if "name" in tool
        }
        tool = available_tools.get(tool_name)
        if tool is None:
            return {
                "ok": False,
                "error": "unknown_tool",
                "message": f"Tool '{tool_name}' is not available",
                "available_tools": sorted(available_tools),
            }

        function = tool.get("function")
        if not callable(function):
            return {
                "ok": False,
                "error": "invalid_tool_configuration",
                "message": f"Tool '{tool_name}' has no callable function",
            }

        self.tool_calls += 1
        try:
            result = function(**arguments)
        except TypeError as exc:
            return {
                "ok": False,
                "error": "invalid_arguments",
                "message": str(exc),
            }
        except Exception:
            return {
                "ok": False,
                "error": "tool_execution_error",
                "message": f"Tool '{tool_name}' failed",
            }

        if not isinstance(result, dict):
            return {
                "ok": False,
                "error": "invalid_tool_result",
                "message": f"Tool '{tool_name}' must return an object",
            }
        return result
