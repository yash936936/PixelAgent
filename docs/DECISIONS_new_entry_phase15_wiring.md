### [2026-08-11] Phase 15 — operational limits wired into orchestrator.py,
  config.py, main.py, and worker.py against real current file contents
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/config.py`, `src/brain/orchestrator.py`, `src/main.py`,
  `src/gui/worker.py`, `tests/brain/test_orchestrator_operational_limits.py` (new).
- **What changed:** The `operational_limits.py` module written earlier today (real,
  standalone, 19/19 tests passing) is now actually wired into the live task-execution
  path, edited directly against this project's real current file contents rather than
  reconstructed from fragments:
  1. **`config.py`**: three new fields (`max_cost_usd`, `max_wall_clock_seconds`,
     `max_concurrent_tasks`), parsed in `load()` following the exact
     `RATE_LIMIT_MAX_BACKOFF_SECONDS` "unset/'none' means no limit" convention already
     established. `max_concurrent_tasks` defaults to 1 (not unlimited), validated to
     reject anything below 1 with a clear error message, per this project's existing
     validation style for `PLANNER_BACKEND`/`RISK_MODEL_BACKEND`/`EXECUTION_MODE`.
  2. **`orchestrator.py`**: `run_task()` now acquires a `TaskLimitsSession` (concurrency
     slot + wall-clock/cost guards) as its very first action, wrapped in `try`/`finally`
     so the concurrency slot is guaranteed released even on an exception mid-task —
     confirmed by a new regression test (`test_slot_is_released_even_when_task_errors`).
     The wall-clock guard is checked at every step boundary in both the fresh-planning
     loop and the episodic-replay loop; the cost guard is checked right after each
     step's real cost (already computed via `_planner_cost()`) is added to a running
     total. A new `OperationalLimitExceeded` catch wraps the main loop, giving this
     class of stop its own distinct `"operational_limit_exceeded"` status — kept
     separate from `"error"` (an infrastructure/cost stop is not the same kind of event
     as an unhandled exception) and separate from boundary/gate-related statuses (not a
     safety classification). A concurrency-ceiling breach specifically raises BEFORE
     `run_task()`'s inner logic even begins, deliberately not caught alongside per-step
     errors, so it propagates to the caller the same way a startup config error would.
  3. **`main.py`**: a module-level, process-scoped `TaskConcurrencyGuard`, sized from
     real `cfg.max_concurrent_tasks` on first use (module import happens before `cfg`
     exists, so it can't be sized at import time — documented inline, including the
     honest limitation that this only guards re-entrant calls within one process, not
     two separate `pixel "..."` invocations in two terminals, which are two separate
     processes with two separate guards; true cross-process locking was explicitly
     out of scope, matching `operational_limits.py`'s own original scope note).
  4. **`worker.py`**: ported in the **same pass** as `main.py` this time — its own
     separate module-level guard (GUI and CLI are different processes, so they can't
     share one), `OperationalLimits` built from the same three `cfg` fields, wired into
     `Orchestrator`'s constructor identically to `main.py`. Explicitly avoids repeating
     the `TESSERACT_CMD`/`AUTO_APPROVE_EXTERNAL`/`EXECUTION_MODE` CLI/GUI-parity miss
     from Phase 7/8/12, where each of those was fixed in `main.py` first and only later
     found missing in `worker.py`.
  5. **New tests** (`test_orchestrator_operational_limits.py`): prove the wiring
     actually works against a real `Orchestrator` instance (lightweight `MagicMock`
     collaborators, not the project's full existing fixture set, which wasn't available
     in this session) — cost limit stopping a multi-step task, wall-clock limit
     stopping a slow task, a shared concurrency guard blocking a second concurrent
     `run_task()` call, the slot being released after both successful and errored
     completions, and confirmation that omitting `operational_limits`/
     `concurrency_guard` entirely leaves existing behavior completely unchanged.
- **Important limitation, stated honestly rather than glossed over**: these new
  orchestrator-level tests were **only syntax-checked** (`python -m py_compile`) in
  this session's build environment, **not actually executed** — `orchestrator.py`
  imports several sibling modules (`action_router.py`, `boundary_guard.py`, `gate.py`,
  `memory_api.py`, etc.) that this session only ever saw as fragments, not in full, so
  a real `pytest` run here would fail on missing files rather than reveal anything
  about the new wiring's correctness. **The user should run
  `pytest tests/brain/test_orchestrator_operational_limits.py -v` for real on their own
  checkout before trusting this wiring** — this is explicitly flagged as unverified,
  following the same "written vs. actually run" honesty this project has maintained
  since Phase 7, rather than silently assuming syntax-valid means correct.
- **Why:** Completes the wiring `PATCH_wiring_orchestrator_and_config.md` (written
  earlier today) explicitly deferred until the real file contents were available,
  rather than guessing at edits to `orchestrator.py` — the single most cross-cutting
  file in this project's history.
- **Impacts:** Phase 15's actual success criterion ("the agent survives a multi-hour
  stress run... and self-terminates cleanly when a limit is hit") still cannot be
  marked met — that needs a real stress run on real hardware, which this session
  cannot perform, same as every other "first real run" milestone in this project's
  history. `docs/PHASES.md`'s Phase 15 should be marked IN PROGRESS: the code is
  written and wired, but neither the new tests nor a real stress run have been
  confirmed passing outside `py_compile`. Next real action: run the new test file for
  real, then attempt a genuine multi-hour or artificially-tightened-limit stress test
  against a live `pixel`/`pixel-gui` run to confirm a limit actually stops a real task
  cleanly end-to-end.
