from typing import Any, Dict, Generator, List, Optional

import pytest

from src.agent.agent import ReActAgent, parse_action, parse_final_answer
from src.core.llm_provider import LLMProvider
from src.tools.tools import TOOL_REGISTRY


class ScriptedLLM(LLMProvider):
    def __init__(self, responses: List[str]):
        super().__init__(model_name="scripted-model")
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


def tools_as_list() -> List[Dict[str, Any]]:
    return list(TOOL_REGISTRY.values())


def test_parsers_accept_documented_formats():
    assert parse_action(
        'Thought: Check inventory.\nAction: check_stock({"item_name": "iPhone"})'
    ) == ("check_stock", {"item_name": "iPhone"})
    assert parse_final_answer("Thought: Done.\nFinal Answer: 45,038,000 VND") == (
        "45,038,000 VND"
    )


def test_parser_rejects_malformed_json():
    with pytest.raises(ValueError):
        parse_action("Action: check_stock({'item_name': 'iPhone'})")


def test_agent_executes_three_tools_and_feeds_observations_back():
    llm = ScriptedLLM(
        [
            (
                "Thought: Check inventory and price.\n"
                'Action: check_stock({"item_name": "iPhone"})'
            ),
            (
                "Thought: Validate the coupon.\n"
                'Action: get_discount({"coupon_code": "WINNER"})'
            ),
            (
                "Thought: Calculate delivery.\n"
                'Action: calc_shipping({"weight": 0.8, "destination": "Hanoi"})'
            ),
            "Final Answer: The grounded total is 45,038,000 VND.",
        ]
    )
    agent = ReActAgent(llm, tools_as_list(), max_steps=5)

    answer = agent.run(
        "Buy 2 iPhones with WINNER and ship 0.8 kg to Hanoi. Total?"
    )

    assert answer == "The grounded total is 45,038,000 VND."
    assert agent.tool_calls == 3
    assert '"price": 25000000' in llm.prompts[1]
    assert '"discount_percent": 10' in llm.prompts[2]
    assert '"shipping_cost": 38000' in llm.prompts[3]


def test_each_action_produces_exactly_one_observation():
    llm = ScriptedLLM(
        [
            'Action: check_stock({"item_name": "MacBook"})',
            "Final Answer: The MacBook is out of stock.",
        ]
    )
    agent = ReActAgent(llm, tools_as_list())

    agent.run("Can I buy a MacBook?")

    observations = [
        entry for entry in agent.history if entry.startswith("Observation:")
    ]
    assert agent.tool_calls == 1
    assert len(observations) == 1
    assert '"status": "out_of_stock"' in observations[0]


def test_unknown_tool_becomes_observation_instead_of_crash():
    llm = ScriptedLLM(
        [
            'Action: search_product({"query": "iPhone"})',
            "Final Answer: I cannot use that tool, so I cannot verify the item.",
        ]
    )
    agent = ReActAgent(llm, tools_as_list())

    answer = agent.run("Find an iPhone")

    assert "cannot verify" in answer
    assert agent.tool_calls == 0
    assert '"error": "unknown_tool"' in llm.prompts[1]


def test_agent_stops_at_max_steps_with_safe_fallback():
    llm = ScriptedLLM(
        [
            'Action: check_stock({"item_name": "iPhone"})',
            'Action: check_stock({"item_name": "iPhone"})',
        ]
    )
    agent = ReActAgent(llm, tools_as_list(), max_steps=2)

    answer = agent.run("Keep checking forever")

    assert answer.startswith("I could not complete")
    assert len(llm.prompts) == 2
    assert agent.tool_calls == 2
