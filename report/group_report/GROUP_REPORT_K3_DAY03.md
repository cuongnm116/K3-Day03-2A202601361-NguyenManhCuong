# Group Report — Lab 3: Chatbot vs ReAct Agent

- **Team Name:** K3 Day 03
- **Team Members:** Nguyen Hoang Viet
- **Evaluation Date:** 2026-07-28
- **Evaluation Mode:** Deterministic scripted providers, no external API

## 1. Executive Summary

We implemented a one-call chatbot baseline and a bounded ReAct Agent with
structured tools. Both systems received the same five inputs.

| System | Successful | Success rate | Safe fallback rate | Avg. LLM steps | Avg. tool calls |
|---|---:|---:|---:|---:|---:|
| Chatbot | 2/5 | 40% | 60% | 1.0 | 0.0 |
| Agent V2 | 5/5 | 100% | 0% | 2.4 | 1.4 |

Formula:

```text
success rate = successful cases / 5
safe fallback rate = safe fallback cases / 5
average steps = total LLM calls / 5
```

The chatbot is sufficient for static policy questions. The Agent provides the
larger benefit for dynamic requests requiring stock, coupon, and shipping
evidence. The trade-off is additional orchestration and LLM steps.

## 2. Architecture and Tooling

The ReAct loop parses one Action, executes one registered tool, appends the
result as an Observation, and calls the provider again. It stops on a Final
Answer or after `max_steps`.

The complete diagram is in `artifacts/react_flowchart.md`.

| Tool | Input contract | Output | Side effect |
|---|---|---|---|
| `check_stock` | `item_name: string` | price, stock, weight, status | Read-only |
| `get_discount` | `coupon_code: string` | validity and discount percent | Read-only |
| `calc_shipping` | positive `weight`, `destination` | cost and estimated days | None |

Tools return structured business errors such as `item_not_found`,
`invalid_input`, and `unsupported_destination` instead of returning `None` or
crashing.

Providers in the repository implement a common `LLMProvider` interface.
Evaluation used a deterministic `ScriptedProvider`; OpenAI, Gemini, and local
adapters were not called.

## 3. Five-Case Evaluation

| Case | Chatbot | Agent V2 | Agent tool path |
|---:|---|---|---|
| 1. Return policy | Correct | Correct | None |
| 2. Working hours | Correct | Correct | None |
| 3. 2 iPhones + WINNER + Hanoi | Safe fallback | Correct: 45,038,000 VND | `check_stock → get_discount → calc_shipping` |
| 4. MacBook + Saigon | Safe fallback | Correctly stops: out of stock | `check_stock` |
| 5. iPad + LEGACY + Saigon | Safe fallback | Correct: 18,030,000 VND, no discount | `check_stock → get_discount → calc_shipping` |

The Agent average rubric score is 12/12. The Chatbot receives 12/12 on static
cases and 5/12 on dynamic safe-fallback cases. These scores reflect the lab
rubric and are recorded per case in `artifacts/evaluation/raw_results.json`.

Latency and token counts are zero in this run because the provider is scripted.
They are deterministic orchestration measurements and must not be presented as
live-model performance.

## 4. Successful Trace

Case 3 follows:

```text
check_stock(iPhone)
→ price 25,000,000; stock 15
get_discount(WINNER)
→ valid; 10%
calc_shipping(0.8, Hanoi)
→ 38,000
Final = (25,000,000 × 2) × 0.9 + 38,000
      = 45,038,000 VND
```

The sanitized raw trace is stored in
`artifacts/traces/multi_step_success_trace.json`.

## 5. Failure RCA and Agent V2

V1 executed the identical action
`check_stock({"item_name": "iPhone"})` twice.

- **Expected path:** one stock check, then Final Answer.
- **First divergence:** step 2 repeats the already completed Action.
- **Root cause:** V1 bounded the loop but did not remember prior Actions.
- **Smallest fix:** fingerprint `(tool name, canonical JSON arguments)` and
  return a `repeated_action` Observation for duplicates.
- **Before/after:** tool executions reduced from 2 to 1.

Evidence:

- `artifacts/traces/repeated_action_failed_trace.json`
- `artifacts/traces/repeated_action_rca.md`
- `tests/test_agent_recovery.py`

## 6. Production Readiness

Current guardrails include bounded steps, registered-tool enforcement,
structured errors, exception wrapping, safe fallback, and repeated-action
detection. `.env`, logs, models, Python caches, and pytest caches are ignored.

Before production use we would add strict schema validation, authenticated
write tools, user confirmation for side effects, persistent trace IDs,
redaction, rate limits, timeouts, retry policies, live-model evaluations, and
monitoring for tokens, latency, cost, and tool error rates.

## 7. Reproduction

```powershell
python -m pytest -q -p no:cacheprovider
python scripts/run_lab_evaluation.py
```

Raw claims and outcomes are in `artifacts/evaluation/raw_results.json`.
