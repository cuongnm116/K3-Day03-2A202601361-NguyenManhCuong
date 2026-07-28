import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.agent import ReActAgent, parse_action
from src.agent.agent_v2 import ReActAgentV2
from src.chatbot.chatbot import Chatbot
from src.core.demo_provider import DemoProvider
from src.tools.tools import TOOL_REGISTRY


def _environment_settings() -> Dict[str, str]:
    file_values = dotenv_values(ROOT / ".env")
    keys = (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "DEFAULT_MODEL",
        "DEFAULT_PROVIDER",
    )
    return {
        key: str(file_values.get(key) or os.getenv(key) or "").strip()
        for key in keys
    }


def get_public_config() -> Dict[str, Any]:
    settings = _environment_settings()
    default_provider = settings["DEFAULT_PROVIDER"].casefold()
    if default_provider not in {"demo", "gemini", "openai"}:
        default_provider = "demo"
    default_model = settings["DEFAULT_MODEL"]
    gemini_model = settings["GEMINI_MODEL"] or (
        default_model
        if default_model.casefold().startswith("gemini-")
        else "gemini-3.6-flash"
    )
    openai_model = settings["OPENAI_MODEL"] or (
        default_model
        if default_provider == "openai" and default_model
        else "gpt-4o"
    )
    return {
        "default_provider": default_provider,
        "gemini_configured": bool(settings["GEMINI_API_KEY"]),
        "gemini_model": gemini_model,
        "openai_configured": bool(settings["OPENAI_API_KEY"]),
        "openai_model": openai_model,
    }


def _safe_provider_error(exc: Exception, provider_mode: str) -> str:
    provider_name = "OpenAI" if provider_mode == "openai" else "Gemini"
    detail = str(exc)
    if "429" in detail or "RESOURCE_EXHAUSTED" in detail:
        return (
            f"{provider_name} đã hết quota hoặc đang bị giới hạn tốc độ "
            "(HTTP 429). "
            "Hãy đợi rồi thử lại, đổi sang model còn quota, bật billing, "
            "hoặc dùng Demo local."
        )
    if "403" in detail or "PERMISSION_DENIED" in detail:
        return (
            f"{provider_name} từ chối quyền truy cập (HTTP 403). Kiểm tra API key, "
            "API restrictions và project chứa key."
        )
    if "404" in detail or "NOT_FOUND" in detail:
        return (
            f"Không tìm thấy model {provider_name} (HTTP 404). Kiểm tra "
            "DEFAULT_MODEL hoặc model riêng của provider trong .env."
        )
    if "400" in detail or "INVALID_ARGUMENT" in detail:
        return (
            f"{provider_name} từ chối request (HTTP 400). Kiểm tra model và nội dung "
            "request."
        )
    return (
        f"{provider_name} request failed. Check the API key, model name, quota, and "
        f"network access. Detail: {type(exc).__name__}"
    )


def _create_provider(mode: str, provider_mode: str):
    provider_system_mode = "chatbot" if mode == "chatbot" else "agent"
    if provider_mode == "demo":
        return DemoProvider(provider_system_mode)
    if provider_mode not in {"gemini", "openai"}:
        raise ValueError("provider must be demo, gemini, or openai")

    settings = _environment_settings()
    if provider_mode == "openai":
        api_key = settings["OPENAI_API_KEY"]
        if not api_key:
            raise ValueError("OPENAI_API_KEY is missing from .env")
        model_name = (
            settings["OPENAI_MODEL"]
            or settings["DEFAULT_MODEL"]
            or "gpt-4o"
        )
        from src.core.openai_provider import OpenAIProvider

        return OpenAIProvider(model_name=model_name, api_key=api_key)

    api_key = settings["GEMINI_API_KEY"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from .env")

    default_model = settings["DEFAULT_MODEL"]
    model_name = settings["GEMINI_MODEL"] or (
        default_model
        if default_model.casefold().startswith("gemini-")
        else "gemini-3.6-flash"
    )
    from src.core.gemini_provider import GeminiProvider

    return GeminiProvider(model_name=model_name, api_key=api_key)


def execute_query(
    mode: str, message: str, provider_mode: str = "demo"
) -> Dict[str, Any]:
    if mode not in {"chatbot", "agent_v1", "agent_v2"}:
        raise ValueError("mode must be chatbot, agent_v1, or agent_v2")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")

    provider = _create_provider(mode, provider_mode)
    if mode == "chatbot":
        result = Chatbot(provider).chat(message)
        return {
            "mode": mode,
            "provider": provider_mode,
            "model": provider.model_name,
            "answer": result["answer"],
            "llm_calls": result["llm_calls"],
            "tool_calls": 0,
            "tool_path": [],
            "trace": [],
        }

    agent_class = ReActAgent if mode == "agent_v1" else ReActAgentV2
    agent = agent_class(
        provider,
        list(TOOL_REGISTRY.values()),
        max_steps=5,
    )
    answer = agent.run(message)
    tool_path = []
    for item in agent.history:
        try:
            action = parse_action(item)
        except (ValueError, json.JSONDecodeError):
            action = None
        if action is not None:
            tool_path.append(action[0])
    return {
        "mode": mode,
        "provider": provider_mode,
        "model": provider.model_name,
        "answer": answer,
        "llm_calls": provider.calls,
        "tool_calls": agent.tool_calls,
        "tool_path": tool_path,
        "trace": agent.history,
    }


class UIRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 20_000:
                raise ValueError("request is too large")
            body = json.loads(self.rfile.read(content_length))
            result = execute_query(
                body.get("mode"),
                body.get("message"),
                body.get("provider") or get_public_config()["default_provider"],
            )
            self._send_json(200, result)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(
                502,
                {
                    "error": _safe_provider_error(
                        exc,
                        body.get("provider")
                        or get_public_config()["default_provider"],
                    )
                },
            )

    def do_GET(self) -> None:
        if self.path == "/api/config":
            self._send_json(200, get_public_config())
            return
        super().do_GET()

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[UI] {self.address_string()} - {format % args}")


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), UIRequestHandler)
    print(f"Lab UI is running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping UI...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
