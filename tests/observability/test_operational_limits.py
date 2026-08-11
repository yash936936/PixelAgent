"""tests/observability/test_operational_limits.py — Phase 15."""

import time

import pytest

from src.observability.operational_limits import (
    CostGuard,
    OperationalLimitExceeded,
    OperationalLimits,
    TaskConcurrencyGuard,
    WallClockGuard,
    acquire_task_limits_session,
)


class TestWallClockGuard:
    def test_no_limit_never_raises(self):
        guard = WallClockGuard(max_seconds=None)
        guard.start()
        guard.check()  # should not raise

    def test_raises_after_budget_exceeded(self):
        guard = WallClockGuard(max_seconds=0.01)
        guard.start()
        time.sleep(0.02)
        with pytest.raises(OperationalLimitExceeded) as exc_info:
            guard.check()
        assert exc_info.value.limit_name == "max_wall_clock_seconds"

    def test_does_not_raise_before_budget_exceeded(self):
        guard = WallClockGuard(max_seconds=10.0)
        guard.start()
        guard.check()  # should not raise, barely any time has passed

    def test_check_before_start_does_not_raise(self):
        guard = WallClockGuard(max_seconds=0.01)
        guard.check()  # start() never called -- should be a safe no-op, not a crash

    def test_elapsed_seconds_before_start_is_zero(self):
        guard = WallClockGuard(max_seconds=10.0)
        assert guard.elapsed_seconds == 0.0

    def test_elapsed_seconds_after_start_increases(self):
        guard = WallClockGuard(max_seconds=10.0)
        guard.start()
        time.sleep(0.01)
        assert guard.elapsed_seconds > 0.0


class TestCostGuard:
    def test_no_limit_never_raises(self):
        guard = CostGuard(max_usd=None)
        guard.check(current_cost_usd=1_000_000.0)  # should not raise

    def test_raises_when_over_budget(self):
        guard = CostGuard(max_usd=1.0)
        with pytest.raises(OperationalLimitExceeded) as exc_info:
            guard.check(current_cost_usd=1.01)
        assert exc_info.value.limit_name == "max_cost_usd"

    def test_does_not_raise_at_exactly_the_limit(self):
        guard = CostGuard(max_usd=1.0)
        guard.check(current_cost_usd=1.0)  # equal to, not over -- should not raise

    def test_does_not_raise_under_budget(self):
        guard = CostGuard(max_usd=1.0)
        guard.check(current_cost_usd=0.50)


class TestTaskConcurrencyGuard:
    def test_unlimited_allows_many_acquires(self):
        guard = TaskConcurrencyGuard(max_concurrent=None)
        for _ in range(10):
            guard.acquire()
        assert guard.active_count == 10

    def test_limit_of_one_blocks_second_acquire(self):
        guard = TaskConcurrencyGuard(max_concurrent=1)
        guard.acquire()
        with pytest.raises(OperationalLimitExceeded) as exc_info:
            guard.acquire()
        assert exc_info.value.limit_name == "max_concurrent_tasks"

    def test_release_frees_a_slot_for_reacquire(self):
        guard = TaskConcurrencyGuard(max_concurrent=1)
        guard.acquire()
        guard.release()
        guard.acquire()  # should not raise -- slot was freed
        assert guard.active_count == 1

    def test_release_never_goes_negative(self):
        guard = TaskConcurrencyGuard(max_concurrent=1)
        guard.release()  # release without a matching acquire
        guard.release()
        assert guard.active_count == 0

    def test_active_count_reflects_multiple_acquires_under_limit(self):
        guard = TaskConcurrencyGuard(max_concurrent=3)
        guard.acquire()
        guard.acquire()
        assert guard.active_count == 2


class TestAcquireTaskLimitsSession:
    def test_returns_a_session_with_all_three_guards_configured(self):
        limits = OperationalLimits(max_cost_usd=5.0, max_wall_clock_seconds=60.0, max_concurrent_tasks=2)
        concurrency_guard = TaskConcurrencyGuard(max_concurrent=2)
        session = acquire_task_limits_session(limits, concurrency_guard)
        assert session.wall_clock.elapsed_seconds >= 0.0
        session.cost.check(current_cost_usd=1.0)  # should not raise
        session.release()

    def test_raises_immediately_if_concurrency_already_at_capacity(self):
        limits = OperationalLimits(max_concurrent_tasks=1)
        concurrency_guard = TaskConcurrencyGuard(max_concurrent=1)
        concurrency_guard.acquire()  # simulate an already-running task
        with pytest.raises(OperationalLimitExceeded):
            acquire_task_limits_session(limits, concurrency_guard)

    def test_release_is_idempotent(self):
        limits = OperationalLimits(max_concurrent_tasks=1)
        concurrency_guard = TaskConcurrencyGuard(max_concurrent=1)
        session = acquire_task_limits_session(limits, concurrency_guard)
        session.release()
        session.release()  # calling twice should not raise or double-decrement
        assert concurrency_guard.active_count == 0

    def test_default_concurrency_limit_is_one(self):
        # Per OperationalLimits' own docstring: defaults to a conservative 1, not
        # unlimited, since this project has never had an explicit multi-task guard
        # before Phase 15.
        limits = OperationalLimits()
        assert limits.max_concurrent_tasks == 1
