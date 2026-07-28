from typing import Any, Dict, Generator, List, Optional, Type

from src.agent.agent import ReActAgent
from src.agent.agent_v2 import ReActAgentV2
from src.core.llm_provider import LLMProvider
from src.tools.tools import TOOL_REGISTRY


class ScriptedLLM(LLMProvider):
    def __init__(self, responses: List[str]):
        super().__init__(model_name="scripted-repeated-action")
        self.responses = iter(responses)
        self.prompts: List[str] = []

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        self.prompts.append(prompt)
        return {
            "content": next(self.responses),
            "usage": {},
            "latency_ms": 0,
            "provider": "scripted",
        }

    def stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        yield ""


def run_repeated_action_scenario(
    agent_class: Type[ReActAgent],
) -> tuple[ReActAgent, ScriptedLLM, str]:
    repeated_action = 'Action: check_stock({"item_name": "iPhone"})'
    llm = ScriptedLLM(
        [
            repeated_action,
            repeated_action,
            "Final Answer: iPhone is in stock at 25,000,000 VND.",
        ]
    )
    agent = agent_class(
        llm=llm,
        tools=list(TOOL_REGISTRY.values()),
        max_steps=3,
    )
    answer = agent.run("Is the iPhone in stock and what is its price?")
    return agent, llm, answer


def test_v1_reexecutes_the_identical_action():
    agent, _, answer = run_repeated_action_scenario(ReActAgent)

    assert "25,000,000 VND" in answer
    assert agent.tool_calls == 2


def test_v2_blocks_the_identical_action_and_returns_error_observation():
    agent, llm, answer = run_repeated_action_scenario(ReActAgentV2)

    assert "25,000,000 VND" in answer
    assert agent.tool_calls == 1
    assert '"error": "repeated_action"' in llm.prompts[2]


def test_v2_resets_repeated_action_memory_between_user_requests():
    repeated_action = 'Action: check_stock({"item_name": "iPhone"})'
    llm = ScriptedLLM(
        [
            repeated_action,
            "Final Answer: First request complete.",
            repeated_action,
            "Final Answer: Second request complete.",
        ]
    )
    agent = ReActAgentV2(llm, list(TOOL_REGISTRY.values()))

    assert agent.run("First request") == "First request complete."
    assert agent.run("Second request") == "Second request complete."
    assert agent.tool_calls == 1
