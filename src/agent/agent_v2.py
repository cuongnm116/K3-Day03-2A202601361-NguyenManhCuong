import json
from typing import Any, Dict, List, Tuple

from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider


class ReActAgentV2(ReActAgent):
    """ReAct Agent V2 with a guard against identical repeated actions."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
    ):
        super().__init__(llm=llm, tools=tools, max_steps=max_steps)
        self._seen_actions: set[Tuple[str, str]] = set()

    def run(self, user_input: str) -> str:
        self._seen_actions = set()
        return super().run(user_input)

    def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        fingerprint = (
            tool_name,
            json.dumps(arguments, ensure_ascii=False, sort_keys=True),
        )
        if fingerprint in self._seen_actions:
            return {
                "ok": False,
                "error": "repeated_action",
                "message": (
                    f"Action '{tool_name}' with the same arguments was already "
                    "executed. Use the previous Observation or choose another action."
                ),
            }

        self._seen_actions.add(fingerprint)
        return super()._execute_tool(tool_name, arguments)
