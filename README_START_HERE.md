# Phase 15 — real wiring pass

Written directly against the real, current contents of your four files —
not reconstructed from fragments this time, since you pasted them in full.

## Files — all four are complete, drop-in replacements

1. **`src/config.py`** — adds `max_cost_usd`, `max_wall_clock_seconds`,
   `max_concurrent_tasks`, plus their env-var parsing in `load()`.
2. **`src/brain/orchestrator.py`** — `run_task()` now acquires a limits
   session first thing, checks wall-clock at every step boundary (both the
   fresh-planning and replay loops), checks cost after each step, and
   catches `OperationalLimitExceeded` with its own distinct status.
3. **`src/main.py`** — a process-scoped concurrency guard, sized from real
   config, wired into `Orchestrator`'s constructor.
4. **`src/gui/worker.py`** — the same wiring, ported in this same pass
   (not left as a later "found missing" fix, learning from the
   `TESSERACT_CMD`/`AUTO_APPROVE_EXTERNAL` precedent).
5. **`src/observability/operational_limits.py`** — unchanged from earlier
   today, included here again so this zip is self-contained.

## Tests

6. **`tests/observability/test_operational_limits.py`** — unchanged,
   genuinely re-run in this session, still 19/19 passing.
7. **`tests/brain/test_orchestrator_operational_limits.py`** — **new, and
   important: only syntax-checked, not actually run.** `orchestrator.py`
   imports several sibling modules I've only ever seen as fragments in this
   conversation, so a real pytest run in my sandbox would fail on missing
   imports, not reveal anything about whether the wiring itself is correct.

## What you need to do before trusting this

```bash
pytest tests/brain/test_orchestrator_operational_limits.py -v
```

Run this for real on your actual checkout. If anything fails, paste the
output back — I'd rather fix a real failure against real output than have
you discover a wiring bug mid-task later.

## Docs

8. **`docs/DECISIONS_new_entry_phase15_wiring.md`** — append to the end of
   your real `docs/DECISIONS.md`.

## After the tests pass

Try an artificially tight limit to confirm the behavior end-to-end, e.g.:

```bash
MAX_WALL_CLOCK_SECONDS=5 python -m src.main "open example.com and describe the page in detail"
```

A task that would normally take longer than 5 seconds should now stop with
`status: operational_limit_exceeded` instead of running to completion —
that's the real proof this phase's success criterion asks for, beyond just
tests passing in isolation.
