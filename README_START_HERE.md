# Phase 14 closeout + Phase 15 start

## Phase 14 closeout (docs only, no code)

1. **`docs/DECISIONS_new_entry_phase14_closeout.md`** — append to the end of your
   real `docs/DECISIONS.md`.
2. **`docs/RELEASE_ENGINEERING.md`** — drop-in replacement for your real
   `docs/RELEASE_ENGINEERING.md`. Marks Phase 14 complete for its achievable scope,
   documents the three still-open items (rollback, Windows-VM Docker variant, the
   eval-score drift).

Also worth doing by hand: update `docs/PHASES.md`'s Phase 14 section status line
to COMPLETE (browser-only/native scope), and `docs/STATUS.md`'s overall progress
line — I don't have full current copies of either in this conversation to safely
regenerate, so this is a manual edit, same caveat as usual.

## Phase 15 start (real, tested code)

1. **`src/observability/operational_limits.py`** — new file, complete and
   self-contained. Three guard classes (`CostGuard`, `WallClockGuard`,
   `TaskConcurrencyGuard`) plus `OperationalLimitExceeded` and a convenience
   `acquire_task_limits_session()` helper.
2. **`tests/observability/test_operational_limits.py`** — new, 16 tests, all
   should pass standalone (no dependency on the rest of the codebase).
3. **`PATCH_wiring_orchestrator_and_config.md`** — **not code.** Explains exactly
   what wiring is needed to make this module actually affect live task runs, and
   why that wiring wasn't attempted blind — it touches `orchestrator.py`,
   `config.py`, `main.py`, and `worker.py`, all four of which have grown real
   cross-cutting complexity this session doesn't have full visibility into.

## To actually finish Phase 15

Run the tests to confirm they pass standalone:

```bash
pytest tests/observability/test_operational_limits.py -v
```

Then, when you're ready for the real wiring pass, paste (or share) the current
full contents of `src/config.py`, `src/brain/orchestrator.py`, `src/main.py`, and
`src/gui/worker.py` — I'll write the actual edits against your real code rather
than guessing at how they currently look. Phase 15 isn't complete until that
wiring happens and a real stress run confirms the limits actually stop a runaway
task, per `docs/PHASES.md`'s own success criterion.
