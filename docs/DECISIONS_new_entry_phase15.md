### [2026-08-11] Phase 14 marked complete (browser-only/native scope); Phase 15 —
  operational safety limits, module written and tested, wiring deferred pending real files
- **Type:** New (multiple) + Design decision
- **File(s) affected:** `src/observability/operational_limits.py` (new),
  `tests/observability/test_operational_limits.py` (new, 16 tests).
- **What changed:**
  1. **Phase 14 marked complete** for its achievable scope (native Windows installer +
     browser-only Docker, both automated and verified end-to-end via `v0.12.4`'s fully
     green release run). Automated rollback and the Windows-VM Docker variant carried
     forward as explicitly acknowledged open items, not silently dropped — see
     `docs/RELEASE_ENGINEERING.md`'s updated status.
  2. **Phase 15 started.** `operational_limits.py` implements three independent, each
     individually-optional hard ceilings beyond the existing `max_steps_per_task`:
     `CostGuard` (checks `LoopAudit`'s already-tracked running cost against a ceiling,
     deliberately not a second source of truth for cost), `WallClockGuard` (a
     **cooperative**, not preemptive, per-task timeout — explicitly documented as unable
     to interrupt a single hung step, only able to stop a task at the next step boundary;
     a true preemptive kill would need a separate-process/thread architecture, out of
     scope here and flagged as future work rather than silently assumed solved), and
     `TaskConcurrencyGuard` (a process-local, thread-safe ceiling on in-flight tasks,
     defaulting to 1 given this project's standing "no multi-user/concurrency model"
     known gap — explicitly NOT cross-process/cross-machine). All three raise a new
     `OperationalLimitExceeded` exception, kept deliberately distinct from
     boundary/risk-related exceptions, matching this project's "fail loud, not silent"
     convention (the confirmation-gate silent-approve bug from 2026-08-01 is the
     cautionary precedent this pattern is designed to avoid repeating).
  3. **Wiring into `orchestrator.py`/`config.py`/`main.py`/`worker.py` deliberately NOT
     done in this pass** — `PATCH_wiring_orchestrator_and_config.md` documents exactly
     what's needed and why it needs the real, current contents of those four files
     (all four have grown significant cross-cutting complexity across nearly every phase
     of this project) rather than a reconstruction from fragments, same discipline
     applied to Phase 13's container-orchestration hooks and tonight's `config.py`
     model-default fix.
- **Why:** Implements `docs/PHASES.md`'s Phase 15 file table's *new* surface area
  (the guard classes) completely and testably, while being honest that the *update*
  surface area (wiring into already-complex existing files) needs the real files in
  hand to do safely, per this project's established practice of not guessing at
  edits to files it can't fully see.
- **Impacts:** `operational_limits.py` is fully unit-tested (16/16 passing) and usable
  standalone right now — but has NO effect on any live task until the wiring pass
  happens. `docs/PHASES.md`'s Phase 15 should be marked IN PROGRESS, not complete —
  its actual success criterion ("the agent survives a multi-hour stress run... and
  self-terminates cleanly when a limit is hit") cannot be tested until wiring is done
  and a real stress run is performed, matching every other phase's "written vs. run"
  distinction in this log.
