# RCA — Repeated Action

| Field | Analysis |
|---|---|
| User input | `Is the iPhone in stock and what is its price?` |
| Expected path | `check_stock` once, then `Final Answer` |
| Actual path V1 | `check_stock` twice, then `Final Answer` |
| First divergence | Step 2: the same tool and arguments are executed again |
| Error class | Loop / orchestration |
| Root cause | V1 has `max_steps` but does not remember previously executed actions |
| Smallest fix | Store `(tool_name, canonical JSON arguments)` fingerprints and reject duplicates |
| Regression test | `tests/test_agent_recovery.py` |
| Before | V1 executes the tool 2 times |
| After | V2 executes the tool 1 time and returns a `repeated_action` Observation |

Reproduce with:

```powershell
python -m pytest tests/test_agent_recovery.py -q -p no:cacheprovider
```
