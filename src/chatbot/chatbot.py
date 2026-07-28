from typing import Any, Dict, Optional

from src.core.llm_provider import LLMProvider


SYSTEM_PROMPT = """
You are a customer-support chatbot for an e-commerce store.

Answer general, static questions clearly and concisely.
You do not have access to inventory, prices, coupon status, shipping fees, or
order systems. When a question requires current store data or an action, say
that you cannot verify it and ask the user to use the store system or contact
support. Never invent tool results and never claim that an order was placed.
""".strip()


class Chatbot:
    """One-call chatbot baseline with no tools or orchestration loop."""

    def __init__(self, llm: LLMProvider, system_prompt: Optional[str] = None):
        self.llm = llm
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    def chat(self, user_message: str) -> Dict[str, Any]:
        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("user_message must be a non-empty string")

        result = self.llm.generate(
            user_message.strip(),
            system_prompt=self.system_prompt,
        )

        return {
            "answer": result["content"],
            "llm_calls": 1,
            "tool_calls": 0,
            "usage": result.get("usage", {}),
            "latency_ms": result.get("latency_ms", 0),
            "provider": result.get("provider", "unknown"),
        }
