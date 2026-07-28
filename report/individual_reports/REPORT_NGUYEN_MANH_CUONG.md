# Individual Report — Lab 3: Chatbot vs ReAct Agent

- **Student Name:** Nguyen Manh Cuong
- **Student ID:** 2A202601361
- **Date:** 2026-07-28

---

## I. Technical Contribution

My role in this lab was mainly on the **review and verification side** of three core modules, working alongside the teammate who wrote the initial implementation:

| Module | My contribution |
|---|---|
| `src/chatbot/chatbot.py` | Reviewed the baseline implementation to confirm it makes exactly one provider call with `tool_calls = 0`, and does not smuggle any pre-computed tool result into the system prompt. Ran `tests/test_chatbot_baseline.py` and checked both the static Q&A case and the multi-step case to confirm the chatbot falls back honestly instead of guessing numbers. |
| `src/agent/agent.py` | Reviewed the ReAct loop (parser → executor → Observation → next provider call) and traced through `max_steps` behavior manually to confirm it terminates instead of looping forever. Ran `tests/test_agent_react_loop.py` and cross-checked the parsed Actions against the tool registry. |
| `src/agent/agent_v2.py` | Reviewed the duplicate-action guard added on top of V1, verified the fingerprinting logic `(tool_name, canonical_json_arguments)` correctly identifies a repeated call, and ran `tests/test_agent_recovery.py` to confirm the fix. |

**How I verified correctness:** rather than just reading the code, I re-ran the full suite (`python -m pytest -q -p no:cacheprovider`) and also executed `scripts/run_lab_evaluation.py` myself to reproduce the 5-case comparison independently, so I could confirm the numbers in the group report weren't just copy-pasted but actually reproducible on a clean run.

- **Documentation:** Confirmed that the Observation returned to the loop always comes from the actual tool function output (never authored by the model), which is the core invariant the whole ReAct design depends on — I checked this specifically in `agent.py` by tracing where the Observation string gets constructed before being appended back into the next prompt.

---

## II. Debugging Case Study

**Problem I investigated:** while running the test suite for `agent.py` (V1) against the query *"Is the iPhone in stock and what is its price?"*, I noticed `check_stock({"item_name": "iPhone"})` was executed twice in the trace, even though the first call already returned both the price and the stock count needed to answer.

**Log source:** `artifacts/traces/repeated_action_failed_trace.json`, cross-checked against the written root cause in `artifacts/traces/repeated_action_rca.md`.

**Diagnosis:** Tracing step by step, step 1 matched the expected path. Step 2 is the first divergence — same tool, same arguments, executed again for no new reason. `max_steps` does bound the loop overall, but it has no way of recognizing "this exact action already ran" versus "the agent is still making progress," so it can't prevent a wasted repeat call on its own. This told me the bug lived in the orchestration logic of `agent.py`, not in `check_stock` itself — the tool's output was correct both times.

**Solution:** This is exactly what `agent_v2.py` fixes: before executing an Action, it computes a fingerprint of `(tool_name, canonical_json_arguments)` and checks it against the actions already executed in the current request. If it's a repeat, the loop returns a structured `repeated_action` Observation instead of calling the tool again — so the model gets useful feedback ("you already did this") rather than silently burning an extra tool call. I confirmed the fix by re-running `tests/test_agent_recovery.py`:

```
V1 tool executions: 2
V2 tool executions: 1
```

---

## III. Personal Insights: Chatbot vs ReAct

1. **Reasoning.** From reviewing both systems side by side, the clearest difference is that `agent.py`'s `Thought` step forces a checkpoint before every action — the model has to state what it still needs before it's allowed to act. `chatbot.py` has no such checkpoint; it goes straight from prompt to final answer, so there's no place in the code where you could catch it about to reason toward the wrong evidence.

2. **Reliability.** Testing both systems on the return-policy and working-hours questions, they performed identically — one provider call, zero tools, both correct. The agent's extra orchestration bought nothing on these two cases. If I had only looked at these two, I would have concluded the extra ReAct machinery is overhead the lab doesn't need. It's only once I ran the multi-step cases (iPhone + coupon + shipping, out-of-stock MacBook) that the gap became obvious — the chatbot had to fall back to admitting uncertainty on all three, while the agent produced grounded, tool-verified answers.

3. **Observation.** The out-of-stock MacBook case was the most instructive one for me while reviewing `agent.py`: the `check_stock` Observation reporting zero stock was enough by itself for the loop to stop early and correctly refuse the purchase, without ever calling `calc_shipping`. That's the practical payoff of the Observation step — each tool result actually changes what the loop does next, instead of the model just continuing to talk.

My overall takeaway from reviewing rather than writing this code first-hand: the value of the ReAct pattern is very task-dependent. For lookups with a single static answer, it's pure overhead. For anything requiring several verified facts chained together, it's the only way to avoid the chatbot's two bad options — hallucinate a number or refuse to answer.

---

## IV. Future Improvements

- **Input validation:** enforce a strict schema (JSON Schema / Pydantic) on every parsed Action before it reaches the executor, instead of trusting the model's output format — this is the first thing I'd want to see hardened after reviewing `agent.py`.
- **Tool resilience:** once tools call real external systems instead of in-memory data, add timeouts, retries, and circuit breakers — the current tools are all synchronous and assume the "backend" never fails.
- **Guardrails for write actions:** all three tools reviewed here are read-only; any future tool with side effects (placing an order, applying a refund) should require explicit user confirmation before `agent_v2.py`'s executor is allowed to run it.
- **Observability:** persist a trace ID per request and redact any personal/payment data before logging, so failures like the repeated-action bug can be diagnosed in production the same way I diagnosed it here from a saved trace file.
- **Evaluation beyond the scripted provider:** the 5-case results are all from a deterministic `ScriptedProvider`, so latency and token counts are zero by construction — a real rollout needs a second evaluation pass against a live model with latency/cost/error-rate tracking.

---

## Reproduction

```powershell
python -m pytest -q -p no:cacheprovider
python scripts/run_lab_evaluation.py
```
