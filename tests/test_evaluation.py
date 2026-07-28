from scripts.run_lab_evaluation import run_evaluation


def test_deterministic_evaluation_covers_all_five_cases():
    report = run_evaluation(write_artifacts=False)

    assert report["case_count"] == 5
    assert len(report["chatbot"]["results"]) == 5
    assert len(report["agent_v2"]["results"]) == 5


def test_evaluation_metrics_match_raw_outcomes():
    report = run_evaluation(write_artifacts=False)
    chatbot = report["chatbot"]["summary"]
    agent = report["agent_v2"]["summary"]

    assert chatbot["successful_cases"] == 2
    assert chatbot["success_rate"] == 0.4
    assert chatbot["safe_fallback_cases"] == 3
    assert chatbot["safe_fallback_rate"] == 0.6
    assert chatbot["average_llm_steps"] == 1.0

    assert agent["successful_cases"] == 5
    assert agent["success_rate"] == 1.0
    assert agent["safe_fallback_cases"] == 0
    assert agent["average_llm_steps"] == 2.4
    assert agent["average_tool_calls"] == 1.4


def test_dynamic_agent_tool_paths_match_expectations():
    report = run_evaluation(write_artifacts=False)
    results = report["agent_v2"]["results"]

    assert results[2]["tool_path"] == [
        "check_stock",
        "get_discount",
        "calc_shipping",
    ]
    assert results[3]["tool_path"] == ["check_stock"]
    assert results[4]["tool_path"] == [
        "check_stock",
        "get_discount",
        "calc_shipping",
    ]
