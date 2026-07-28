import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

from scripts.run_ui import (
    UIRequestHandler,
    _safe_provider_error,
    execute_query,
    get_public_config,
)


def test_ui_chatbot_mode_uses_no_tools():
    result = execute_query(
        "chatbot",
        "Tôi muốn mua 2 iPhone dùng mã WINNER và giao tới Hà Nội.",
    )

    assert result["mode"] == "chatbot"
    assert result["llm_calls"] == 1
    assert result["tool_calls"] == 0
    assert result["tool_path"] == []
    assert "không thể xác minh" in result["answer"]


def test_ui_agent_mode_runs_real_three_tool_path():
    result = execute_query(
        "agent_v2",
        (
            "Tôi muốn mua 2 iPhone dùng mã WINNER và giao 0.8 kg "
            "tới Hà Nội. Tổng bao nhiêu?"
        ),
    )

    assert result["answer"].startswith("Tổng tiền có căn cứ là 45,038,000 VND")
    assert result["llm_calls"] == 4
    assert result["tool_calls"] == 3
    assert result["tool_path"] == [
        "check_stock",
        "get_discount",
        "calc_shipping",
    ]


def test_ui_agent_stops_when_product_is_out_of_stock():
    result = execute_query(
        "agent_v2",
        "Tôi có thể mua 1 MacBook và giao tới Sài Gòn không?",
    )

    assert "hết hàng" in result["answer"]
    assert result["tool_path"] == ["check_stock"]


def test_ui_rejects_invalid_mode_and_empty_message():
    try:
        execute_query("invalid", "hello")
        raise AssertionError("Expected invalid mode to fail")
    except ValueError:
        pass

    try:
        execute_query("agent_v2", "hello", provider_mode="invalid")
        raise AssertionError("Expected invalid provider to fail")
    except ValueError:
        pass


def test_ui_http_server_serves_page_and_chat_endpoint():
    server = ThreadingHTTPServer(("127.0.0.1", 0), UIRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "ReAct Lab Console" in html

        with urlopen(
            f"http://127.0.0.1:{port}/api/config", timeout=2
        ) as response:
            config = json.loads(response.read())
            assert response.status == 200
            assert config["default_provider"] in {"demo", "gemini", "openai"}
            assert "GEMINI_API_KEY" not in config

        payload = json.dumps(
            {
                "mode": "agent_v2",
                "provider": "demo",
                "message": "Mua 1 MacBook",
            }
        ).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{port}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            result = json.loads(response.read())
            assert response.status == 200
            assert result["tool_path"] == ["check_stock"]
            assert "hết hàng" in result["answer"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    try:
        execute_query("agent_v2", " ")
        raise AssertionError("Expected empty message to fail")
    except ValueError:
        pass


def test_ui_exposes_agent_v1_and_v2_as_separate_modes():
    v1 = execute_query("agent_v1", "Mua 1 iPhone")
    v2 = execute_query("agent_v2", "Mua 1 iPhone")

    assert v1["mode"] == "agent_v1"
    assert v2["mode"] == "agent_v2"
    assert v1["tool_path"] == ["check_stock"]
    assert v2["tool_path"] == ["check_stock"]


def test_public_config_never_exposes_api_key():
    config = get_public_config()

    assert "GEMINI_API_KEY" not in config
    assert "OPENAI_API_KEY" not in config
    assert set(config) == {
        "default_provider",
        "gemini_configured",
        "gemini_model",
        "openai_configured",
        "openai_model",
    }


def test_gemini_quota_error_is_user_friendly():
    message = _safe_provider_error(
        RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"),
        "gemini",
    )

    assert "hết quota" in message
    assert "HTTP 429" in message


def test_openai_quota_error_names_the_provider():
    message = _safe_provider_error(
        RuntimeError("429 rate limit exceeded"),
        "openai",
    )

    assert "OpenAI" in message


def test_demo_provider_recognizes_extended_catalog_products():
    result = execute_query(
        "agent_v2",
        "Tôi muốn mua 1 Samsung Galaxy S24 và giao 0.4 kg tới Đà Nẵng",
    )

    assert result["tool_path"] == ["check_stock", "calc_shipping"]
    assert "23,022,000 VND" in result["answer"]
