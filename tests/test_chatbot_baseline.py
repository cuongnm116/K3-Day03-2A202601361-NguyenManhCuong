from typing import Any, Dict, Generator, Optional

from src.chatbot.chatbot import Chatbot
from src.core.llm_provider import LLMProvider


class FakeLLM(LLMProvider):
    """Deterministic provider used to test orchestration without an API."""

    def __init__(self, response: str):
        super().__init__(model_name="fake-model")
        self.response = response
        self.generate_calls = 0
        self.last_prompt: Optional[str] = None
        self.last_system_prompt: Optional[str] = None

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        self.generate_calls += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        return {
            "content": self.response,
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
            "latency_ms": 1,
            "provider": "fake",
        }

    def stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        yield self.response


def test_static_question_uses_exactly_one_llm_call_and_no_tools():
    llm = FakeLLM(
        "You may return an unused product within 30 days with proof of purchase."
    )
    chatbot = Chatbot(llm)

    result = chatbot.chat("What is your return policy?")

    assert result["answer"] == llm.response
    assert result["llm_calls"] == 1
    assert result["tool_calls"] == 0
    assert llm.generate_calls == 1


def test_multistep_question_returns_safe_fallback_without_tool_evidence():
    llm = FakeLLM(
        "I cannot verify the current price, coupon, stock, or shipping fee "
        "without access to the store systems."
    )
    chatbot = Chatbot(llm)

    result = chatbot.chat(
        "I want to buy 2 iPhones using code WINNER and ship to Hanoi. Total?"
    )

    assert "cannot verify" in result["answer"]
    assert result["llm_calls"] == 1
    assert result["tool_calls"] == 0
    assert llm.generate_calls == 1
    assert "inventory" in llm.last_system_prompt
