from unittest.mock import MagicMock

from PIL import Image

from src.brain.orchestrator import MaxStepsExceeded, Orchestrator
from src.confirmation.gate import GateDecision


def _img(color):
    return Image.new("RGB", (10, 10), color)


def make_orchestrator(planner_steps, mouse_keyboard=None, replanner=None, max_steps=5):
    driver = MagicMock()
    driver.current_url.return_value = "https://example.com"
    driver.current_title.return_value = "Example"

    action_router = MagicMock()
    action_router.execute.return_value = {"status": "executed"}

    gate = MagicMock()
    gate.request_approval.return_value = GateDecision(verdict="approved")

    logger = MagicMock()

    planner = MagicMock()
    planner.next_step.side_effect = planner_steps

    orch = Orchestrator(
        planner=planner,
        driver=driver,
        action_router=action_router,
        gate=gate,
        logger=logger,
        max_steps=max_steps,
        mouse_keyboard=mouse_keyboard,
        replanner=replanner,
    )
    return orch, action_router, gate, logger


def test_task_completes_on_done_step():
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[{"action": "done", "description": "finished", "target_type": "web", "params": {}}]
    )
    result = orch.run_task("do something trivial")
    assert result["status"] == "done"
    action_router.execute.assert_not_called()


def test_local_step_executes_without_gate():
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[
            {"action": "navigate", "description": "go to site", "target_type": "web",
             "params": {"url": "https://x.com"}},
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ]
    )
    result = orch.run_task("go to x.com")
    assert result["status"] == "done"
    gate.request_approval.assert_not_called()
    action_router.execute.assert_called_once()


def test_external_step_goes_through_gate():
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[
            {"action": "click", "description": "Star the repo", "target_type": "web",
             "params": {"selector": "#star"}},
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ]
    )
    result = orch.run_task("star the repo")
    assert result["status"] == "done"
    gate.request_approval.assert_called_once()


def test_denied_gate_stops_task():
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[
            {"action": "click", "description": "Star the repo", "target_type": "web",
             "params": {"selector": "#star"}},
        ]
    )
    gate.request_approval.return_value = GateDecision(verdict="denied")
    result = orch.run_task("star the repo")
    assert result["status"] == "stopped_denied"
    action_router.execute.assert_not_called()


def test_max_steps_exceeded_raises():
    # Planner never returns "done" -> should exhaust the step budget.
    step = {"action": "navigate", "description": "loop", "target_type": "web", "params": {"url": "x"}}
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[step, step, step], max_steps=3
    )
    try:
        orch.run_task("infinite task")
        assert False, "expected MaxStepsExceeded"
    except MaxStepsExceeded:
        pass


def test_verification_skipped_without_screenshot_source():
    # No mouse_keyboard and driver.screenshot mocked to raise -> verification
    # disabled, task still completes normally.
    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[
            {"action": "navigate", "description": "go", "target_type": "web",
             "params": {"url": "https://x.com"}},
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
        replanner=MagicMock(),  # replanner present but no screenshot source
    )
    result = orch.run_task("go somewhere")
    assert result["status"] == "done"


def test_replan_triggered_on_screen_mismatch():
    mouse_keyboard = MagicMock()
    # First call before-shot, second after-shot for step 1 (mismatch: black->black = no visible change,
    # but action expects change) -> triggers replan; then replanned step matches (before != after).
    black = _img((0, 0, 0))
    white = _img((255, 255, 255))
    mouse_keyboard.screenshot.side_effect = [black, black, black, white]

    replanner = MagicMock()
    corrected_step = {"action": "click", "description": "corrected click",
                       "target_type": "web", "params": {"selector": "#retry"}}
    replanner.correct.return_value = corrected_step

    orch, action_router, gate, logger = make_orchestrator(
        planner_steps=[
            {"action": "click", "description": "Local click", "target_type": "web",
             "params": {"selector": "#thing"}},
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
        mouse_keyboard=mouse_keyboard,
        replanner=replanner,
    )
    result = orch.run_task("click the thing")
    assert result["status"] == "done"
    replanner.correct.assert_called_once()
    # Original step + corrected step both attempted execution
    assert action_router.execute.call_count == 2
