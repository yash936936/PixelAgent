# Wiring Phase 15 into orchestrator.py and config.py

Same situation as every other "patch note" tonight: `operational_limits.py` is a
complete, real, fully-tested new file — but wiring it INTO `orchestrator.py`'s
`run_task()` loop and `config.py`'s settings needs your real current versions of
those files in front of me, not a guess reconstructed from grep fragments. Both
files have grown real complexity across this project's history (rate limits,
execution mode, semantic risk layer, injection signal, replay logic) — a blind edit
risks silently breaking one of those existing behaviors.

## What needs to happen, concretely, once you share the real files

### `src/config.py`
Add three new fields, following the exact pattern `log_retention_days`/
`execution_mode` already established:

```python
max_cost_usd: float | None = None          # env MAX_COST_USD, unset = no limit
max_wall_clock_seconds: float | None = None  # env MAX_WALL_CLOCK_SECONDS, unset = no limit
max_concurrent_tasks: int = 1              # env MAX_CONCURRENT_TASKS, default 1
```

Parsed in `load()` the same way `log_retention_days` is — `os.environ.get(...)`
with a type conversion and a clear error message on an invalid value (see how
`risk_model_backend`'s validation raises a `ValueError` with an explanatory
message; match that style).

### `src/brain/orchestrator.py`
1. `Orchestrator.__init__` (or wherever `memory`/`llm_risk_judge` etc. are already
   accepted as constructor params) takes an optional `operational_limits:
   OperationalLimits | None` and a shared, process-wide
   `concurrency_guard: TaskConcurrencyGuard` (constructed once in `main.py`/
   `worker.py`, not per-task, so the concurrency ceiling is actually shared across
   calls — see below).
2. At the very top of `run_task()`, before the existing max-step-budget loop
   starts: call `acquire_task_limits_session(...)`, wrapped so `session.release()`
   is guaranteed to run via `try`/`finally` (or a `with`-statement wrapper, if you
   add a `__enter__`/`__exit__` to `TaskLimitsSession` — not added here, left to
   your judgment based on how the rest of `orchestrator.py`'s error handling is
   structured, which I can't see in full).
3. At each step boundary (right alongside wherever `max_steps_per_task` is already
   checked): call `session.wall_clock.check()`.
4. Right after `LoopAudit`'s `est_cost` is updated for a step (wherever that
   happens today — per `docs/DECISIONS.md`'s Phase 4/`2026-07-12` entries, this is
   already tracked, just not gated on): call
   `session.cost.check(current_running_cost)`.
5. Catch `OperationalLimitExceeded` the same way `MaxStepsExceeded` (or whatever
   the existing max-step exception is called) is caught — log it via
   `logger.log_event()` with a distinct, clearly-named event type (e.g.
   `operational_limit_exceeded`), and end the task with `status: "error"` (or a new
   distinct status like `"limit_exceeded"` if that reads better against the
   existing status vocabulary — again, need the real file to judge this
   consistently).

### `src/main.py` and `src/gui/worker.py`
Both need a **shared** `TaskConcurrencyGuard` instance — constructed once at
process startup (not per-task-run), matching the existing CLI/GUI-parity lesson
this project learned the hard way in Phase 7/8 (`TESSERACT_CMD`/
`AUTO_APPROVE_EXTERNAL` fixed in `main.py` first, found missing in `worker.py`
later — don't repeat that miss here; wire both in the same pass).

## Why this wasn't attempted blind

Every prior "patch note" tonight followed this same discipline (`config.py`'s
model-default fix, the Phase 13 container-orchestration hooks) — not because
writing plausible-looking wiring code is hard, but because `orchestrator.py`
specifically is the single most cross-cutting file in this project (per
`docs/DECISIONS.md`, it's been touched in nearly every phase since Phase 1), and a
confidently-wrong edit there risks silently breaking real, tested safety behavior
(the confirmation gate, the boundary guard, the semantic risk layer) rather than
just failing loudly and obviously.

## What to send me for the real wiring pass

Paste (or share) the current full contents of:
- `src/config.py`
- `src/brain/orchestrator.py`
- `src/main.py`
- `src/gui/worker.py`

and I'll write the actual diffs/`str_replace` edits against your real code, not a
reconstruction.
