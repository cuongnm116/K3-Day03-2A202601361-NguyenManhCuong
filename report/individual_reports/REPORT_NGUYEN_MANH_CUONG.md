# Individual Report — Lab 3: Chatbot vs ReAct Agent

- **Student Name:** Nguyen Manh Cuong
- **Student ID:** 2A202601361
- **Date:** 2026-07-28

---

## I. Technical Contribution

My assigned part of the lab was the **baseline system**: build the plain chatbot with a safe fallback behavior, and write the test coverage for both the chatbot and the tools it deliberately does *not* have access to.

| # | Task | File(s) |
|---|---|---|
| 9 | Built the Chatbot baseline and its safe fallback behavior | `src/chatbot/chatbot.py` |
| 10 | Wrote tests for the Chatbot and the tool suite | `tests/test_chatbot_baseline.py`, `tests/test_tools.py` |

**`src/chatbot/chatbot.py`:** The `Chatbot` class is intentionally the simplest possible baseline — one `llm.generate()` call, no loop, no tool access at all (`tool_calls` is hardcoded to `0` in the returned dict, not just "usually zero"). The part I focused on was the **safe fallback**, which lives entirely in the system prompt rather than in code logic: the chatbot is explicitly told it has no access to inventory, prices, coupons, shipping, or order systems, and that it must say it cannot verify the answer instead of inventing a number or claiming an order was placed. This matters because a single-call chatbot has no way to check its own answer against reality — the only lever available is instructing the model up front to refuse gracefully rather than guess. I also added the guard clause at the top of `chat()` that rejects empty/non-string input before it ever reaches the provider, so a bad call fails fast with a clear `ValueError` instead of silently generating a response to an empty prompt.

**`tests/test_chatbot_baseline.py`:** I wrote a `FakeLLM` deterministic stand-in for the real provider so the chatbot's orchestration could be tested without any API cost or network dependency. Two cases matter most:
- `test_static_question_uses_exactly_one_llm_call_and_no_tools` — confirms a simple question like the return policy costs exactly 1 LLM call and 0 tool calls.
- `test_multistep_question_returns_safe_fallback_without_tool_evidence` — feeds a question that needs live data (price + coupon + shipping) and asserts the answer contains an honest "cannot verify" instead of a fabricated total, and specifically checks that the word "inventory" appears in the system prompt actually sent to the model — i.e. the fallback instruction was really delivered, not just present in the source file.

**`tests/test_tools.py`:** Since the chatbot has no tools, this suite exists to pin down exactly what the *agent* side would be working with, so both systems are being compared against the same ground truth. I covered: `check_stock` for a found item, an unknown item (`item_not_found` instead of a crash), a missing argument (`invalid_input`), and an explicit `out_of_stock` status case (`stock == 0` but `ok == True`, since "found but unavailable" is a different outcome than "not found"). Same pattern for `get_discount` (valid/expired/unknown/missing) and `calc_shipping` (valid Hanoi rate, missing weight, missing destination, negative weight, unsupported destination). I also added a determinism check confirming repeated calls with the same input return equal — but not the same mutable — objects, and coverage for the extended catalog/coupon/shipping-zone data (including accented vs. plain destination aliases like "Đà Nẵng" / "da nang" resolving to the same result).

---

## II. Debugging Case Study

**Problem I found:** while writing `test_multistep_question_returns_safe_fallback_without_tool_evidence`, my first version of the assertion only checked that `"cannot verify"` appeared in the answer string. That passed even in a run where I temporarily broke the system prompt (removed the "never invent tool results" line) — because the `FakeLLM` I wrote just returns whatever fixed string I gave it, regardless of what system prompt it received. The test looked green but wasn't actually verifying that the fallback instruction was wired through correctly.

**Where I looked:** `tests/test_chatbot_baseline.py`, specifically how `FakeLLM.generate()` records `last_system_prompt`.

**Diagnosis:** The `FakeLLM` already stores `last_system_prompt` for exactly this reason, but my first test wasn't using it — I was only asserting on the output text, not on what was actually sent to the provider. That's a classic false-positive in a test built around a fixed/scripted response: the fake always returns the same content no matter what prompt it's given, so an assertion on the fake's output can't tell you whether the *input* was correct.

**Fix:** I added `assert "inventory" in llm.last_system_prompt` to the test, which checks the actual system prompt that reached the (fake) provider, not just the canned response. Re-running with the safe-fallback instruction deliberately removed from `chatbot.py` now correctly fails the test, confirming it actually catches the regression it's meant to catch.

```
Before fix: test passes even with the fallback instruction removed (false positive)
After fix:  test fails immediately if the fallback instruction is removed (correct)
```

---

## III. Personal Insights: Chatbot vs ReAct

1. **Reasoning.** Building the chatbot side made the contrast concrete for me: `chatbot.py` has exactly one place where behavior can be steered — the system prompt — because there's no loop, no intermediate step, nothing to inspect between input and output. Whatever the fallback instruction says is the whole safety mechanism. The agent, by contrast, has a structural checkpoint (`Thought` → `Action` → `Observation`) where it can be *shown* it doesn't have enough information yet, rather than only being *told* in advance what it can't do.

2. **Reliability.** On the two static questions (return policy, working hours) my chatbot performed identically to the agent — 1 call, correct answer, no wasted machinery. That's exactly what the baseline is supposed to do well. The difference only shows up on the three dynamic questions, where the chatbot has no way to check a price or stock count, so the safe fallback is the *correct* behavior, but it's also a dead end — the user gets an honest "I can't verify this" instead of an actual answer. Writing the fallback made me appreciate that "safe" and "useful" are two different goals, and the baseline can only ever hit the first one.

3. **Observation feedback.** The clearest gap for me, coming from the chatbot side, is that my system has no equivalent of an Observation. It cannot check `check_stock` and change its answer based on the real result — it can only be instructed in advance to admit uncertainty. Reading the agent's trace on the out-of-stock MacBook case (where the `check_stock` Observation with `stock == 0` was enough for the loop to stop and correctly refuse the purchase) showed me exactly what my baseline is missing: a feedback signal from the real world, not just a well-written prompt.

My takeaway from building the baseline specifically: a chatbot with a good fallback is not a lesser version of an agent — it's the right choice for anything static — but it has a hard ceiling on any question that needs current, verifiable data, and no amount of prompt engineering can substitute for an actual tool call.

---

## IV. Future Improvements

- **Fallback testing at scale:** extend `test_chatbot_baseline.py` with a larger set of paraphrased dynamic questions to make sure the safe-fallback behavior generalizes, not just for the two exact phrasings currently tested.
- **Tool test coverage for edge cases:** add tests for boundary values in `tools.py` (e.g. `weight = 0`, extremely large weights, case-sensitivity edge cases beyond the accented-destination check already covered).
- **Structured fallback signal:** right now the chatbot's "I cannot verify" is just plain text; returning a structured flag (e.g. `{"needs_tool_access": true}`) alongside the answer would let a calling application detect the fallback programmatically instead of string-matching.
- **Shared fixtures:** `FakeLLM` currently lives only in `test_chatbot_baseline.py` — moving it to a shared `conftest.py` would let the agent tests reuse the same deterministic provider instead of each maintaining a separate fake.
- **Prompt-versioning tests:** since the whole safety mechanism for the chatbot lives in the system prompt string, adding a regression test that pins the exact required phrases (as I did with `"inventory"`) for every safety-relevant clause would catch future prompt edits that accidentally weaken the fallback.

---

## Reproduction

```powershell
python -m pytest tests/test_chatbot_baseline.py tests/test_tools.py -q -p no:cacheprovider
```
