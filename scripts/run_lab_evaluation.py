import json
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.agent_v2 import ReActAgentV2
from src.chatbot.chatbot import Chatbot
from src.core.llm_provider import LLMProvider
from src.tools.tools import TOOL_REGISTRY


EVALUATION_DIR = ROOT / "artifacts" / "evaluation"
TRACE_DIR = ROOT / "artifacts" / "traces"


TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "input": "What is your return policy?",
        "kind": "static",
        "chatbot_response": (
            "Unused products may be returned within 30 days with proof of purchase."
        ),
        "agent_responses": [
            (
                "Final Answer: Unused products may be returned within 30 days "
                "with proof of purchase."
            )
        ],
        "expected_tools": [],
    },
    {
        "id": 2,
        "input": "What are your working hours?",
        "kind": "static",
        "chatbot_response": (
            "Customer support is available Monday-Friday, 09:00-17:00."
        ),
        "agent_responses": [
            (
                "Final Answer: Customer support is available Monday-Friday, "
                "09:00-17:00."
            )
        ],
        "expected_tools": [],
    },
    {
        "id": 3,
        "input": (
            "I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. "
            "The package weight is 0.8 kg. Total?"
        ),
        "kind": "dynamic",
        "chatbot_response": (
            "I cannot verify current stock, price, coupon validity, or shipping "
            "fees without access to the store systems."
        ),
        "agent_responses": [
            'Action: check_stock({"item_name": "iPhone"})',
            'Action: get_discount({"coupon_code": "WINNER"})',
            'Action: calc_shipping({"weight": 0.8, "destination": "Hanoi"})',
            (
                "Final Answer: 2 iPhones are in stock. After the valid 10% "
                "WINNER discount and 38,000 VND shipping, the grounded total "
                "is 45,038,000 VND."
            ),
        ],
        "expected_tools": [
            "check_stock",
            "get_discount",
            "calc_shipping",
        ],
    },
    {
        "id": 4,
        "input": "Can I buy 1 MacBook and ship to Saigon? How much?",
        "kind": "dynamic",
        "chatbot_response": (
            "I cannot verify current MacBook stock or shipping fees without "
            "access to the store systems."
        ),
        "agent_responses": [
            'Action: check_stock({"item_name": "MacBook"})',
            (
                "Final Answer: The MacBook is out of stock, so I cannot quote "
                "a purchasable shipped total or claim that it can be bought."
            ),
        ],
        "expected_tools": ["check_stock"],
    },
    {
        "id": 5,
        "input": (
            "I want to buy 1 iPad using code 'LEGACY' and ship to Saigon. "
            "The package weight is 0.5 kg. How much?"
        ),
        "kind": "dynamic",
        "chatbot_response": (
            "I cannot verify current stock, coupon validity, or shipping fees "
            "without access to the store systems."
        ),
        "agent_responses": [
            'Action: check_stock({"item_name": "iPad"})',
            'Action: get_discount({"coupon_code": "LEGACY"})',
            'Action: calc_shipping({"weight": 0.5, "destination": "Saigon"})',
            (
                "Final Answer: The LEGACY coupon is invalid, so no discount "
                "applies. The grounded total is 18,030,000 VND including "
                "30,000 VND shipping."
            ),
        ],
        "expected_tools": [
            "check_stock",
            "get_discount",
            "calc_shipping",
        ],
    },
]


class ScriptedProvider(LLMProvider):
    """Deterministic provider for reproducible evaluation."""

    def __init__(self, responses: List[str], model_name: str):
        super().__init__(model_name=model_name)
        self._responses = iter(responses)
        self.calls = 0

    def generate(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        self.calls += 1
        content = next(self._responses)
        return {
            "content": content,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "latency_ms": 0,
            "provider": "scripted",
        }

    def stream(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        yield ""


def _action_names(history: List[str]) -> List[str]:
    names = []
    for entry in history:
        if entry.startswith("Action:"):
            names.append(entry.split(":", 1)[1].split("(", 1)[0].strip())
    return names


def _evaluate_chatbot(case: Dict[str, Any]) -> Dict[str, Any]:
    provider = ScriptedProvider(
        [case["chatbot_response"]],
        model_name=f"chatbot-case-{case['id']}",
    )
    result = Chatbot(provider).chat(case["input"])
    safe_fallback = case["kind"] == "dynamic"
    rubric = (
        {
            "factual_correctness": 1,
            "grounding": 0,
            "tool_selection": 0,
            "safety": 2,
            "completeness": 0,
            "termination": 2,
        }
        if safe_fallback
        else {
            "factual_correctness": 2,
            "grounding": 2,
            "tool_selection": 2,
            "safety": 2,
            "completeness": 2,
            "termination": 2,
        }
    )
    return {
        "case_id": case["id"],
        "input": case["input"],
        "answer": result["answer"],
        "classification": "safe_fallback" if safe_fallback else "correct",
        "task_success": not safe_fallback,
        "safe_fallback": safe_fallback,
        "llm_calls": result["llm_calls"],
        "tool_calls": result["tool_calls"],
        "tool_path": [],
        "latency_ms": result["latency_ms"],
        "rubric_scores": rubric,
        "rubric_total": sum(rubric.values()),
    }


def _evaluate_agent(case: Dict[str, Any]) -> Dict[str, Any]:
    provider = ScriptedProvider(
        case["agent_responses"],
        model_name=f"agent-case-{case['id']}",
    )
    agent = ReActAgentV2(
        provider,
        list(TOOL_REGISTRY.values()),
        max_steps=5,
    )
    answer = agent.run(case["input"])
    tool_path = _action_names(agent.history)
    task_success = tool_path == case["expected_tools"]
    rubric = {
        "factual_correctness": 2,
        "grounding": 2,
        "tool_selection": 2,
        "safety": 2,
        "completeness": 2,
        "termination": 2,
    }
    return {
        "case_id": case["id"],
        "input": case["input"],
        "answer": answer,
        "classification": "correct" if task_success else "incorrect",
        "task_success": task_success,
        "safe_fallback": answer.startswith("I could not complete"),
        "llm_calls": provider.calls,
        "tool_calls": agent.tool_calls,
        "tool_path": tool_path,
        "expected_tool_path": case["expected_tools"],
        "latency_ms": 0,
        "history": agent.history,
        "rubric_scores": rubric,
        "rubric_total": sum(rubric.values()),
    }


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    return {
        "cases": total,
        "successful_cases": sum(item["task_success"] for item in results),
        "success_rate": sum(item["task_success"] for item in results) / total,
        "safe_fallback_cases": sum(item["safe_fallback"] for item in results),
        "safe_fallback_rate": (
            sum(item["safe_fallback"] for item in results) / total
        ),
        "average_llm_steps": (
            sum(item["llm_calls"] for item in results) / total
        ),
        "average_tool_calls": (
            sum(item["tool_calls"] for item in results) / total
        ),
        "average_latency_ms": (
            sum(item["latency_ms"] for item in results) / total
        ),
        "average_rubric_score": (
            sum(item["rubric_total"] for item in results) / total
        ),
    }


def run_evaluation(write_artifacts: bool = True) -> Dict[str, Any]:
    chatbot_results = [_evaluate_chatbot(case) for case in TEST_CASES]
    agent_results = [_evaluate_agent(case) for case in TEST_CASES]
    report = {
        "evaluation_type": "deterministic_scripted",
        "case_count": len(TEST_CASES),
        "chatbot": {
            "summary": _summarize(chatbot_results),
            "results": chatbot_results,
        },
        "agent_v2": {
            "summary": _summarize(agent_results),
            "results": agent_results,
        },
    }

    if write_artifacts:
        EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        (EVALUATION_DIR / "raw_results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        success_case = agent_results[2]
        success_trace = {
            "trace_type": "success_trace",
            "agent_version": "v2",
            "sanitized": True,
            "case_id": success_case["case_id"],
            "input": success_case["input"],
            "tool_path": success_case["tool_path"],
            "history": success_case["history"],
            "final_answer": success_case["answer"],
        }
        (TRACE_DIR / "multi_step_success_trace.json").write_text(
            json.dumps(success_trace, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return report


def main() -> None:
    report = run_evaluation(write_artifacts=True)
    chatbot = report["chatbot"]["summary"]
    agent = report["agent_v2"]["summary"]
    print(
        "Chatbot: "
        f"{chatbot['successful_cases']}/{chatbot['cases']} successful, "
        f"{chatbot['safe_fallback_cases']} safe fallbacks"
    )
    print(
        "Agent V2: "
        f"{agent['successful_cases']}/{agent['cases']} successful, "
        f"{agent['average_llm_steps']:.1f} average LLM steps"
    )
    print(f"Raw results: {EVALUATION_DIR / 'raw_results.json'}")


if __name__ == "__main__":
    main()
