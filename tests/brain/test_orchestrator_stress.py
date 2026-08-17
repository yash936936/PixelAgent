"""
tests/brain/test_orchestrator_stress.py — Phase 15 stress/stability testing.

Honest scope, stated up front: this is NOT the real multi-hour run against real
Playwright/Chromium and real OS-level mouse/keyboard on real Windows hardware that
docs/PHASES.md's Phase 15 success criterion ultimately describes ("memory leak,
orphaned process, or runaway cost" -- the orphaned-process/browser-memory-leak part
of that specifically means real Chromium processes, which this sandboxed Linux test
environment has no way to launch or measure). That real run still needs to happen
separately, on real hardware, per docs/STATUS.md.

What THIS module actually does, and can honestly claim: drives hundreds of
back-to-back Orchestrator.run_task() calls through the REAL orchestrator.py loop
(not a re-implementation of it) with lightweight fakes standing in for
planner/driver/action_router/gate (same fake style as
test_orchestrator_operational_limits.py, which this file is a stress-scale sibling
of), and a REAL Logger writing REAL files to a tmp_path -- so it genuinely exercises
Python-level resource management under repeated load: process RSS growth, Python
thread-count growth, TaskConcurrencyGuard slot leakage, and log-file accumulation/
pruning under real disk I/O. These are real, catchable classes of bug even without a
real browser -- a slot leak, an unclosed file handle, or unbounded growth in Python
object counts across iterations would show up here exactly as it would in a real
multi-hour run, just without the browser-specific failure modes layered on top.

Kept in tests/brain/ (not a separate top-level "stress" directory) since it drives
orchestrator.py exactly like every other test in this directory -- it differs in
iteration COUNT, not in what it's testing.
"""
from __future__ import annotations

import gc
import itertools
import resource
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.brain.orchestrator import Orchestrator
from src.brain.risk_classifier import Risk
from src.observability.logger import Logger, prune_old_logs
from src.observability.operational_limits import (
    OperationalLimitExceeded,
    OperationalLimits,
    TaskConcurrencyGuard,
)

# Kept modest enough to run in a normal CI job (seconds, not the real multi-hour
# run) while still being large enough to surface a genuine per-iteration leak --
# a leak that only shows up after 10,000 iterations but not 300 is a real
# category of bug this count wouldn't catch, but that's true of any bounded
# stress test; see this module's docstring for what's explicitly out of scope.
_STRESS_ITERATIONS = 300


def _make_stress_orchestrator(log_dir: Path, operational_limits=None, concurrency_guard=None):
    """Same fake shape as test_orchestrator_operational_limits.py's
    _make_orchestrator(), reused rather than re-invented -- but wired to a REAL
    Logger (not a MagicMock) writing to log_dir, since log-file accumulation
    under repeated task load is exactly one of the things this module is meant
    to catch."""
    planner = MagicMock()
    planner.next_step.side_effect = [{"action": "done"}]
    planner.last_call_cost = 0.0001  # nonzero so LoopAudit.est_cost genuinely accumulates

    driver = MagicMock()
    driver.is_launched = False

    action_router = MagicMock()
    action_router.execute.return_value = {"status": "executed"}

    gate = MagicMock()

    logger = Logger(log_dir)

    risk_classifier = MagicMock()
    risk_classifier.classify_with_confidence.return_value = (Risk.LOCAL, True)
    risk_classifier.needs_confirmation.return_value = False

    return Orchestrator(
        planner=planner,
        driver=driver,
        action_router=action_router,
        gate=gate,
        logger=logger,
        max_steps=100,
        risk_classifier=risk_classifier,
        operational_limits=operational_limits,
        concurrency_guard=concurrency_guard,
        log_dir=log_dir,
    )


class TestRepeatedTaskStability:
    """Runs many tasks back-to-back through the real orchestrator loop and
    checks for the Python-level resource-leak classes described in this
    module's docstring."""

    def test_concurrency_guard_never_leaks_a_slot_across_many_tasks(self, tmp_path):
        """If TaskConcurrencyGuard.release() were ever skipped on one code
        path (e.g. an exception the original wiring didn't route through the
        finally block), active_count would creep upward run over run until
        every subsequent task permanently fails with
        OperationalLimitExceeded -- exactly the silent, slow-onset failure
        mode a single-task unit test structurally cannot catch, since it
        would look completely fine for the first 1, 2, even 50 tasks."""
        limits = OperationalLimits(max_concurrent_tasks=1)
        guard = TaskConcurrencyGuard(max_concurrent=1)

        for i in range(_STRESS_ITERATIONS):
            orch = _make_stress_orchestrator(
                tmp_path / f"run_{i}", operational_limits=limits, concurrency_guard=guard
            )
            result = orch.run_task(f"stress task {i}")
            assert result is not None
            # The slot must be fully released by the time run_task() returns --
            # a real multi-hour run launches its NEXT task immediately after,
            # so any lingering slot would show up as exactly this assertion
            # failing on the very next iteration, not eventually.
            assert guard.active_count == 0, (
                f"concurrency slot leaked after task {i}: active_count="
                f"{guard.active_count}, expected 0"
            )

    def test_process_rss_does_not_grow_unbounded_across_many_tasks(self, tmp_path):
        """Coarse but real: samples this process's own max resident set size
        (ru_maxrss, stdlib `resource` -- no psutil dependency needed) before
        and after a batch of tasks. ru_maxrss is a high-water mark, not a
        live reading, so this can't catch a leak that peaks and is later
        reclaimed -- it catches the class of bug that matters most for a
        long-running desktop agent: memory that never comes back down."""
        gc.collect()
        rss_before_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        guard = TaskConcurrencyGuard(max_concurrent=1)
        for i in range(_STRESS_ITERATIONS):
            orch = _make_stress_orchestrator(tmp_path / f"rss_{i}", concurrency_guard=guard)
            orch.run_task(f"rss stress task {i}")

        gc.collect()
        rss_after_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # High-water-mark growth across 300 trivial single-step tasks should
        # be small -- generous 150MB ceiling (not a tight bound) since
        # ru_maxrss is platform-sensitive and this test's job is to catch a
        # real runaway leak (unbounded growth), not to pin an exact number.
        growth_kb = rss_after_kb - rss_before_kb
        assert growth_kb < 150_000, (
            f"process RSS high-water mark grew by {growth_kb / 1024:.1f}MB across "
            f"{_STRESS_ITERATIONS} tasks -- possible leak. Before={rss_before_kb}KB "
            f"After={rss_after_kb}KB"
        )

    def test_thread_count_returns_to_baseline_after_many_tasks(self, tmp_path):
        """orchestrator.py's own loop is synchronous (no threading) per its
        module-level convention, but TaskConcurrencyGuard uses a
        threading.Lock -- this test exists to catch a future regression
        where some code path spawns a thread per task and never joins it,
        which would show up as thread_count growing linearly with iteration
        count rather than staying flat."""
        baseline = threading.active_count()

        guard = TaskConcurrencyGuard(max_concurrent=1)
        for i in range(_STRESS_ITERATIONS):
            orch = _make_stress_orchestrator(tmp_path / f"threads_{i}", concurrency_guard=guard)
            orch.run_task(f"thread stress task {i}")

        assert threading.active_count() == baseline, (
            f"thread count grew from {baseline} to {threading.active_count()} "
            f"across {_STRESS_ITERATIONS} tasks -- possible thread leak"
        )

    def test_log_files_accumulate_and_prune_correctly_under_repeated_load(self, tmp_path):
        """Each real task run creates its own real task_*.jsonl file
        (Logger's actual behavior, not mocked) -- confirms Phase 15's log-dir
        growth concern is real (N tasks -> N files, unbounded without
        pruning) and that prune_old_logs() (Phase 8, already unit-tested in
        isolation in test_logger.py) still does its job against a real
        backlog of many genuinely-created files, not just the handful
        existing tests construct by hand."""
        log_dir = tmp_path / "shared_logs"
        guard = TaskConcurrencyGuard(max_concurrent=1)

        n = 50  # smaller than _STRESS_ITERATIONS -- this test's cost is
        # dominated by real file I/O per task, not worth paying 300x for
        for i in range(n):
            orch = _make_stress_orchestrator(log_dir, concurrency_guard=guard)
            orch.run_task(f"log stress task {i}")

        task_files = list(log_dir.glob("task_*.jsonl"))
        assert len(task_files) == n, (
            f"expected {n} real task log files, found {len(task_files)}"
        )

        # prune_old_logs(retention_days<=0) means "keep everything" by
        # design (logger.py's own docstring) -- NOT "delete everything," so
        # exercising real pruning here means actually pushing every file's
        # mtime into the past and using a real positive retention window,
        # not retention_days=0 (an earlier version of this test wrongly
        # assumed 0 meant "prune all," which isn't what the documented
        # contract says).
        import os
        import time

        long_ago = time.time() - (365 * 86400)
        for f in task_files:
            os.utime(f, (long_ago, long_ago))

        deleted = prune_old_logs(log_dir, retention_days=14)
        assert deleted == n, f"expected prune_old_logs to remove all {n} files, removed {deleted}"
        assert list(log_dir.glob("task_*.jsonl")) == []


class TestRepeatedLimitEnforcementUnderLoad:
    """Confirms the three Phase 15 guards keep firing correctly across many
    consecutive tasks, not just the first one or two -- e.g. a guard that
    resets its internal state incorrectly between tasks could pass a single-
    task unit test but silently stop enforcing after the Nth task."""

    def test_cost_limit_fires_on_every_single_task_across_many_runs(self, tmp_path):
        limits = OperationalLimits(max_cost_usd=0.00001)  # any real cost trips it
        guard = TaskConcurrencyGuard(max_concurrent=1)

        exceeded_count = 0
        for i in range(_STRESS_ITERATIONS):
            orch = _make_stress_orchestrator(
                tmp_path / f"cost_{i}", operational_limits=limits, concurrency_guard=guard
            )
            result = orch.run_task(f"cost stress task {i}")
            if result.get("status") == "operational_limit_exceeded":
                exceeded_count += 1
            # Whether the guard fires or the task completes, the slot must
            # still be released -- a limit-triggered task is exactly the
            # path most likely to skip a normal-completion cleanup step if
            # the exception handling were ever wired wrong.
            assert guard.active_count == 0

        assert exceeded_count == _STRESS_ITERATIONS, (
            f"cost limit only fired on {exceeded_count}/{_STRESS_ITERATIONS} tasks -- "
            f"expected every task to exceed a near-zero cost ceiling"
        )

    def test_concurrency_limit_blocks_a_true_overlap_every_time(self, tmp_path):
        """Simulates real overlap (not just sequential reuse): acquires the
        one available slot directly, then confirms _STRESS_ITERATIONS
        separate attempts to start a new task while it's held are ALL
        correctly rejected -- not just the first one, in case some
        rejection path had a subtle off-by-one that let a later attempt
        slip through."""
        guard = TaskConcurrencyGuard(max_concurrent=1)
        guard.acquire()  # simulate one real task already in flight

        try:
            for i in range(_STRESS_ITERATIONS):
                orch = _make_stress_orchestrator(tmp_path / f"overlap_{i}", concurrency_guard=guard)
                with pytest.raises(OperationalLimitExceeded):
                    orch.run_task(f"overlap stress task {i}")
        finally:
            guard.release()

        # Confirms the guard is still in a clean, usable state afterward --
        # a real task can now actually run.
        assert guard.active_count == 0
        orch = _make_stress_orchestrator(tmp_path / "after_overlap", concurrency_guard=guard)
        result = orch.run_task("task after overlap window closes")
        assert result is not None
        assert guard.active_count == 0
