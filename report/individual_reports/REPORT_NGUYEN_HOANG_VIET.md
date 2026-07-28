# Individual Report — Lab 3: Chatbot vs ReAct Agent

- **Student Name:** Nguyen Hoang Viet
- **Student ID:** 2A202601940
- **Date:** 2026-07-28

## I. Technical Contribution

I implemented the following modules:

- `src/chatbot/chatbot.py`: one-call baseline with zero tool calls.
- `src/tools/tools.py`: deterministic stock, coupon, and shipping tools.
- `src/agent/agent.py`: parser, executor, bounded ReAct loop, and fallback.
- `src/agent/agent_v2.py`: repeated-action guard.
- `scripts/run_lab_evaluation.py`: reproducible five-case comparison.
- Tests for the chatbot, tools, Agent V1, Agent V2, and evaluation metrics.

The provider returns model output, while the application parses Actions and
executes tools. Tool results are serialized into Observations before the next
provider call. The model never executes a Python function or supplies its own
trusted Observation.

## II. Debugging Case Study

### Problem

Agent V1 executed the same `check_stock` Action twice even though the first
Observation already contained price and stock.

### Evidence and first divergence

The failed trace is
`artifacts/traces/repeated_action_failed_trace.json`. Step 1 follows the
expected path. Step 2 is the first divergence because it repeats the same tool
and arguments instead of using the existing Observation.

### Diagnosis

`max_steps` prevented an infinite loop but did not prevent redundant tool
execution. The fault was therefore in loop orchestration rather than catalog
data or the `check_stock` function.

### Fix

Agent V2 stores a canonical fingerprint of each executed Action. A duplicate
returns a structured `repeated_action` Observation without running the tool
again. The regression test shows:

```text
V1 tool executions: 2
V2 tool executions: 1
```

The guard is reset for each new user request so independent requests do not
interfere.

## III. Personal Insights

The Thought/Action format is valuable because it exposes which fact the model
needs next. Reliability comes from Observation data supplied by the
application, not from the wording of the Thought.

The Agent is not universally better. On return-policy and working-hours
questions, both systems used one provider call and no tool. Agent
orchestration adds complexity without improving those static answers.

The difference appears on dynamic cases. The chatbot safely admitted it could
not verify stock, coupon validity, or shipping fees. The Agent collected those
facts and produced grounded totals. For an out-of-stock MacBook, the stock
Observation caused it to stop early instead of calculating shipping or
claiming a purchase was possible.

Evaluation must therefore include the path, not only the final text: tool
selection, Observation evidence, recovery, safety, and termination all affect
whether an answer is trustworthy.

## IV. Future Improvements

- Validate every Action against JSON Schema or Pydantic models.
- Add timeouts, retries, rate limiting, and circuit breakers for external tools.
- Require authentication and explicit confirmation for tools with side effects.
- Redact secrets and personal data before persistent logging.
- Add live-provider evaluation separately from deterministic orchestration tests.
- Track token usage, latency percentiles, cost, error rate, and fallback rate.
- Use a state-machine framework when workflows require branching or human review.

## Reproduction

```powershell
python -m pytest -q -p no:cacheprovider
python scripts/run_lab_evaluation.py
```
