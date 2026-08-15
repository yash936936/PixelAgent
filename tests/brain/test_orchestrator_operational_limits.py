"""tests/brain/test_orchestrator_operational_limits.py — Phase 15 wiring.

Proves operational_limits.py's guards actually stop a real Orchestrator.run_task()
call, not just that the standalone module works in isolation
(tests/observability/test_operational_limits.py already covers that). Uses
lightweight fakes rather than the project's full existing mock fixtures, since
this file only has orchestrator.py's real current contents to work from, not
the rest of the test suite's shared fixture file (conftest.py) -- these fakes
are intentionally minimal and self-contained so they don't assume anything
about fixtures this session hasn't seen in full.
"""

from unittest.mock import MagicMock

import pytest

from src.brain.orchestrator import Orchestrator
from src.brain.risk_classifier import Risk
from src.observability.operational_limits import (
    OperationalLimitExceeded,
    OperationalLimits,
    TaskConcurrencyGuard,
)


def _make_orchestrator(operational_limits=None, concurrency_guard=None, planner_steps=None):
    """Builds an Orchestrator with the minimum real/fake collaborators needed
    to drive run_task() through a few steps. planner_steps is a list of step
    dicts to return in order, ending naturally with {"action": "done"} unless
    the caller wants the loop to keep going (e.g. for a wall-clock test that
    should never reach "done" within the test's short timeout)."""
    planner = MagicMock()
    if planner_steps is None:
        planner_steps = [{"action": "done"}]
    planner.next_step.side_effect = planner_steps
    planner.last_call_cost = 0.0

    driver = MagicMock()
    driver.is_launched = False

    action_router = MagicMock()
    action_router.execute.return_value = {"status": "executed"}

    gate = MagicMock()

    logger = MagicMock()

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
    )


class TestOrchestratorWithoutOperationalLimits:
    def test_default_construction_behaves_unchanged(self):
        """No operational_limits/concurrency_guard passed -- should behave
        exactly as before this phase, per the constructor's own docstring."""
        orch = _make_orchestrator()
        result = orch.run_task("do a trivial local thing")
        assert result["status"] == "done"


class TestCostLimitWiring:
    def test_task_stops_with_operational_limit_status_when_cost_exceeded(self):
        planner = MagicMock()
        # Two real steps then done -- each step "costs" money via last_call_cost.
        planner.next_step.side_effect = [
            {"action": "click", "target_type": "web", "params": {"selector": "#a"}},
            {"action": "click", "target_type": "web", "params": {"selector": "#b"}},
            {"action": "done"},
        ]
        planner.last_call_cost = 10.0  # each step "costs" $10

        driver = MagicMock()
        driver.is_launched = False
        action_router = MagicMock()
        action_router.execute.return_value = {"status": "executed"}
        gate = MagicMock()
        logger = MagicMock()
        risk_classifier = MagicMock()
        risk_classifier.classify_with_confidence.return_value = (Risk.LOCAL, True)
        risk_classifier.needs_confirmation.return_value = False

        limits = OperationalLimits(max_cost_usd=15.0)  # one $10 step is fine, two isn't

        orch = Orchestrator(
            planner=planner,
            driver=driver,
            action_router=action_router,
            gate=gate,
            logger=logger,
            max_steps=100,
            risk_classifier=risk_classifier,
            operational_limits=limits,
        )
        result = orch.run_task("do two costly things")
        assert result["status"] == "operational_limit_exceeded"
        # Confirm the distinct event was logged, not folded into a generic error.
        logged_events = [call.args for call in logger.log_event.call_args_list]
        assert any(
            isinstance(args[1], dict) and args[1].get("limit_name") == "max_cost_usd"
            for args in logged_events
        )

    def test_task_completes_normally_when_under_cost_limit(self):
        planner = MagicMock()
        planner.next_step.side_effect = [
            {"action": "click", "target_type": "web", "params": {"selector": "#a"}},
            {"action": "done"},
        ]
        planner.last_call_cost = 1.0

        driver = MagicMock()
        driver.is_launched = False
        action_router = MagicMock()
        action_router.execute.return_value = {"status": "executed"}
        gate = MagicMock()
        logger = MagicMock()
        risk_classifier = MagicMock()
        risk_classifier.classify_with_confidence.return_value = (Risk.LOCAL, True)
        risk_classifier.needs_confirmation.return_value = False

        limits = OperationalLimits(max_cost_usd=100.0)

        orch = Orchestrator(
            planner=planner, driver=driver, action_router=action_router, gate=gate, logger=logger,
            max_steps=100, risk_classifier=risk_classifier, operational_limits=limits,
        )
        result = orch.run_task("do one cheap thing")
        assert result["status"] == "done"


class TestWallClockLimitWiring:
    def test_task_stops_with_operational_limit_status_when_time_exceeded(self):
        import time

        def slow_next_step(*args, **kwargs):
            time.sleep(0.02)
            return {"action": "click", "target_type": "web", "params": {"selector": "#a"}}

        planner = MagicMock()
        planner.next_step.side_effect = slow_next_step
        planner.last_call_cost = 0.0

        driver = MagicMock()
        driver.is_launched = False
        action_router = MagicMock()
        action_router.execute.return_value = {"status": "executed"}
        gate = MagicMock()
        logger = MagicMock()
        risk_classifier = MagicMock()
        risk_classifier.classify_with_confidence.return_value = (Risk.LOCAL, True)
        risk_classifier.needs_confirmation.return_value = False

        limits = OperationalLimits(max_wall_clock_seconds=0.03)  # ~1-2 slow steps' worth

        orch = Orchestrator(
            planner=planner, driver=driver, action_router=action_router, gate=gate, logger=logger,
            max_steps=1000, risk_classifier=risk_classifier, operational_limits=limits,
        )
        result = orch.run_task("do something that takes too long")
        assert result["status"] == "operational_limit_exceeded"

    def test_task_completes_normally_when_fast_enough(self):
        orch = _make_orchestrator(operational_limits=OperationalLimits(max_wall_clock_seconds=30.0))
        result = orch.run_task("do a quick local thing")
        assert result["status"] == "done"


class TestConcurrencyLimitWiring:
    def test_second_task_blocked_while_first_is_still_running(self):
        """Simulates two orchestrators sharing one guard, where the first
        never releases its slot (as if still mid-task) -- the second should
        be refused immediately at run_task()'s very first line, before any
        planning happens at all."""
        shared_guard = TaskConcurrencyGuard(max_concurrent=1)
        shared_guard.acquire()  # simulate an already-in-flight first task

        orch2 = _make_orchestrator(
            operational_limits=OperationalLimits(max_concurrent_tasks=1),
            concurrency_guard=shared_guard,
        )
        with pytest.raises(OperationalLimitExceeded) as exc_info:
            orch2.run_task("a second task that shouldn't be allowed to start")
        assert exc_info.value.limit_name == "max_concurrent_tasks"

    def test_slot_is_released_after_task_completes_allowing_a_new_one(self):
        shared_guard = TaskConcurrencyGuard(max_concurrent=1)

        orch1 = _make_orchestrator(
            operational_limits=OperationalLimits(max_concurrent_tasks=1),
            concurrency_guard=shared_guard,
        )
        result1 = orch1.run_task("first task")
        assert result1["status"] == "done"
        assert shared_guard.active_count == 0  # released via the finally in run_task()

        # A second, separate orchestrator sharing the same guard should now
        # be able to acquire the freed slot.
        orch2 = _make_orchestrator(
            operational_limits=OperationalLimits(max_concurrent_tasks=1),
            concurrency_guard=shared_guard,
        )
        result2 = orch2.run_task("second task, after the first released its slot")
        assert result2["status"] == "done"

    def test_slot_is_released_even_when_task_errors(self):
        """Confirms the finally-based release in run_task() covers the error
        path too, not just the happy path -- a slot leak here would
        permanently jam the concurrency guard after any single failed task,
        which would be a much worse outcome than the limit it's meant to
        enforce."""
        planner = MagicMock()
        planner.next_step.side_effect = RuntimeError("simulated planner crash")
        planner.last_call_cost = 0.0

        driver = MagicMock()
        driver.is_launched = False
        action_router = MagicMock()
        gate = MagicMock()
        logger = MagicMock()
        risk_classifier = MagicMock()

        shared_guard = TaskConcurrencyGuard(max_concurrent=1)

        orch = Orchestrator(
            planner=planner, driver=driver, action_router=action_router, gate=gate, logger=logger,
            max_steps=10, risk_classifier=risk_classifier,
            operational_limits=OperationalLimits(max_concurrent_tasks=1),
            concurrency_guard=shared_guard,
        )
        with pytest.raises(RuntimeError):
            orch.run_task("a task whose planner call raises")
        assert shared_guard.active_count == 0
