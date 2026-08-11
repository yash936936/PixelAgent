"""src/observability/operational_limits.py — Phase 15: operational safety limits.

Per docs/PHASES.md's Phase 15: hard ceilings BEYOND the existing max_steps_per_task
(which already exists per Phase 1's risk_classifier.py / orchestrator.py) -- max cost
per task, a per-task wall-clock timeout with forced termination, and (lightly) max
concurrent tasks. This module is deliberately self-contained and dependency-free
(stdlib only: time, threading, dataclasses) so it can be unit-tested and reasoned
about without needing orchestrator.py's real current internals in front of us --
wiring it INTO orchestrator.py is a separate, smaller step described in
PATCH_orchestrator_phase15.md, once the real current file is available to edit
directly rather than guessed at.

Design choice, stated plainly: this module raises exceptions rather than silently
capping/truncating behavior, matching this project's existing "fail loud, not
silent" pattern (boundary_guard.py never silently downgrades a match; the
confirmation gate never silently defaults to approved after the 2026-08-01 fix).
A task that hits a real operational limit should look like an explicit, loggable
stop -- not output that quietly got smaller or slower without anyone noticing.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


class OperationalLimitExceeded(Exception):
    """Raised when a task exceeds a configured operational ceiling.

    Deliberately a distinct exception type from anything risk/boundary-related --
    this is an infrastructure/cost guard, not a safety-classification decision, and
    should never be caught by the same handling path as a boundary_guard block or a
    gate denial (those are meaningful safety events; this is "the machine ran too
    long/cost too much/too many are running at once").
    """

    def __init__(self, limit_name: str, message: str):
        self.limit_name = limit_name
        super().__init__(message)


@dataclass
class OperationalLimits:
    """Configuration for Phase 15's hard ceilings.

    All three are independent and each individually optional (None disables that
    specific check) -- mirrors this project's existing config.py convention of
    every new safety-adjacent setting having an explicit, documented default rather
    than an implicit one (see AUTO_APPROVE_EXTERNAL's off-by-default precedent,
    docs/DECISIONS.md 2026-08-01).

    max_cost_usd: hard ceiling on LoopAudit.est_cost for a single task. None = no
        cost ceiling (existing behavior, unchanged default).
    max_wall_clock_seconds: hard ceiling on total task wall-clock time, checked
        cooperatively at each step boundary (NOT a hard preemptive kill of a stuck
        LLM call or a hung OS-level action mid-step -- see the "Known limitation"
        note below). None = no timeout (existing behavior, unchanged default).
    max_concurrent_tasks: hard ceiling on how many tasks TaskConcurrencyGuard will
        allow to be "in flight" at once, process-wide. None = unlimited (existing
        behavior, unchanged default -- PixelAgent has always been effectively
        single-task per docs/STATUS.md's "no multi-user/concurrency model" known
        gap, so this defaults to a conservative 1 rather than None once actually
        wired in; see PATCH_orchestrator_phase15.md).
    """

    max_cost_usd: float | None = None
    max_wall_clock_seconds: float | None = None
    max_concurrent_tasks: int | None = 1


class WallClockGuard:
    """Cooperative wall-clock timeout checker for a single task.

    KNOWN LIMITATION, stated plainly rather than glossed over: this is a
    cooperative check, not a preemptive kill. It can only stop a task AT THE NEXT
    step boundary where orchestrator.py calls .check() -- it cannot interrupt a
    single step that is itself hung (e.g. a real OS-level mouse/keyboard action
    that never returns, or a Playwright call stuck against a frozen page). A truly
    preemptive kill would need to run the task in a separate process/thread and
    terminate it externally, which is a materially bigger architectural change than
    this phase's scope -- flagged here explicitly as future work, not silently
    assumed solved by this class's existence. What this DOES catch: a task that is
    technically making forward progress (planning/executing/verifying steps) but
    has been doing so for too long in aggregate -- e.g. a slow LLM backend, a
    replan loop that keeps "succeeding" at each individual step but never
    finishing the task, or simple human error (a wildly over-scoped instruction).
    """

    def __init__(self, max_seconds: float | None):
        self._max_seconds = max_seconds
        self._start: float | None = None

    def start(self) -> None:
        self._start = time.monotonic()

    def check(self) -> None:
        """Call at each step boundary. Raises OperationalLimitExceeded if over budget."""
        if self._max_seconds is None or self._start is None:
            return
        elapsed = time.monotonic() - self._start
        if elapsed > self._max_seconds:
            raise OperationalLimitExceeded(
                "max_wall_clock_seconds",
                f"Task exceeded its wall-clock budget: {elapsed:.1f}s elapsed, "
                f"{self._max_seconds:.1f}s allowed. Stopping at this step boundary "
                f"rather than mid-step -- see WallClockGuard's known cooperative-"
                f"only limitation.",
            )

    @property
    def elapsed_seconds(self) -> float:
        if self._start is None:
            return 0.0
        return time.monotonic() - self._start


class CostGuard:
    """Checks a running task's accumulated cost against a hard ceiling.

    Deliberately takes the current cost as a parameter to .check() rather than
    tracking it internally -- LoopAudit (src/observability/logger.py, Phase 4/8)
    already owns the authoritative running est_cost figure; this class should never
    become a second, potentially-drifting source of truth for cost. It's a pure
    threshold check over a value orchestrator.py already has.
    """

    def __init__(self, max_usd: float | None):
        self._max_usd = max_usd

    def check(self, current_cost_usd: float) -> None:
        if self._max_usd is None:
            return
        if current_cost_usd > self._max_usd:
            raise OperationalLimitExceeded(
                "max_cost_usd",
                f"Task exceeded its cost budget: ${current_cost_usd:.4f} spent, "
                f"${self._max_usd:.4f} allowed.",
            )


class TaskConcurrencyGuard:
    """Process-wide ceiling on how many tasks may run "in flight" at once.

    Thread-safe (a plain threading.Lock, not asyncio -- matches this project's
    existing synchronous orchestrator.run_task() design; no part of this codebase
    is async as of Phase 14 per every prior DECISIONS.md entry describing
    orchestrator.py's loop). Deliberately process-local, not cross-process/
    cross-machine -- multi-instance/distributed concurrency limiting is out of
    scope here and would need a shared external store (e.g. a lock file, a small
    local DB row), not attempted in this pass. This guard only protects against
    the realistic single-machine case: a person (or a script) accidentally
    launching a second `pixel`/`pixel-gui` task while one is already mid-run on the
    same machine, which given docs/STATUS.md's "no multi-user/concurrency model"
    known gap has never been an explicitly guarded-against case before now.
    """

    def __init__(self, max_concurrent: int | None):
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()
        self._active_count = 0

    def acquire(self) -> None:
        with self._lock:
            if self._max_concurrent is not None and self._active_count >= self._max_concurrent:
                raise OperationalLimitExceeded(
                    "max_concurrent_tasks",
                    f"Cannot start a new task: {self._active_count} task(s) already "
                    f"running, limit is {self._max_concurrent}. This is a "
                    f"process-local guard -- see TaskConcurrencyGuard's docstring "
                    f"for what it does and doesn't cover.",
                )
            self._active_count += 1

    def release(self) -> None:
        with self._lock:
            self._active_count = max(0, self._active_count - 1)

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_count


@dataclass
class TaskLimitsSession:
    """Convenience bundle for a single task run, combining all three guards.

    orchestrator.py's run_task() should construct one of these at task start
    (via acquire_task_limits_session() below, which also handles the
    TaskConcurrencyGuard.acquire()/.release() pairing correctly even on an
    exception), call .wall_clock.check() at each step boundary (alongside the
    existing max_steps_per_task check), and .cost.check(current_cost) after each
    step's cost is added to LoopAudit -- see PATCH_orchestrator_phase15.md for the
    exact call sites once the real orchestrator.py is available to edit directly.
    """

    wall_clock: WallClockGuard
    cost: CostGuard
    _concurrency_guard: TaskConcurrencyGuard = field(repr=False)
    _released: bool = field(default=False, repr=False)

    def release(self) -> None:
        """Idempotent -- safe to call more than once (e.g. from both a normal
        completion path and a finally block)."""
        if not self._released:
            self._concurrency_guard.release()
            self._released = True


def acquire_task_limits_session(
    limits: OperationalLimits, concurrency_guard: TaskConcurrencyGuard
) -> TaskLimitsSession:
    """Acquires a concurrency slot and returns a session bundling all three guards.

    Raises OperationalLimitExceeded immediately (without partially starting
    anything) if the concurrency ceiling is already at capacity -- callers should
    treat this the same way they'd treat a boundary_guard block: log it, surface it
    to the user/trace, do not silently retry in a loop.
    """
    concurrency_guard.acquire()
    wall_clock = WallClockGuard(limits.max_wall_clock_seconds)
    wall_clock.start()
    cost = CostGuard(limits.max_cost_usd)
    return TaskLimitsSession(wall_clock=wall_clock, cost=cost, _concurrency_guard=concurrency_guard)
