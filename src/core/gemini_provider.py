import time
from typing import Any, Dict, Generator, Optional

from google import genai
from google.genai import types

from src.core.llm_provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API provider using Google's current google-genai SDK."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        api_key: Optional[str] = None,
    ):
        if not api_key:
            raise ValueError("Gemini API key is required")
        super().__init__(model_name, api_key)
        self.client = genai.Client(api_key=api_key)
        self.calls = 0

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        self.calls += 1
        start_time = time.perf_counter()
        config = (
            types.GenerateContentConfig(system_instruction=system_prompt)
            if system_prompt
            else None
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage_metadata = response.usage_metadata
        prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
        completion_tokens = (
            getattr(usage_metadata, "candidates_token_count", 0) or 0
        )
        total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0

        return {
            "content": response.text or "",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "latency_ms": latency_ms,
            "provider": "gemini",
        }

    def stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        self.calls += 1
        config = (
            types.GenerateContentConfig(system_instruction=system_prompt)
            if system_prompt
            else None
        )
        for chunk in self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
