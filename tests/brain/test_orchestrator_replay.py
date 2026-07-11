from unittest.mock import MagicMock

from src.brain.orchestrator import Orchestrator
from src.confirmation.gate import GateDecision


def make_orchestrator_with_memory(memory, planner_steps=None, max_steps=5):
    driver = MagicMock()
    driver.current_url.return_value = "https://example.com"
    driver.current_title.return_value = "Example"

    action_router = MagicMock()
    action_router.execute.return_value = {"status": "executed"}

    gate = MagicMock()
    gate.request_approval.return_value = GateDecision(verdict="approved")

    logger = MagicMock()

    planner = MagicMock()
    planner.next_step.side_effect = planner_steps or []

    orch = Orchestrator(
        planner=planner,
        driver=driver,
        action_router=action_router,
        gate=gate,
        logger=logger,
        max_steps=max_steps,
        memory=memory,
    )
    return orch, action_router, gate, planner, logger


def test_matching_episode_is_replayed_without_planner_calls():
    memory = MagicMock()
    replayed_step = {"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}}
    episode = MagicMock(id=1, steps=[replayed_step])
    memory.find_replay.return_value = episode

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(memory)
    result = orch.run_task("open x.com")

    assert result["status"] == "done"
    planner.next_step.assert_not_called()
    action_router.execute.assert_called_once_with(replayed_step)
    memory.record_task.assert_called_once_with("open x.com", result["history"], "done", edited=False)


def test_no_matching_episode_falls_back_to_fresh_planning():
    memory = MagicMock()
    memory.find_replay.return_value = None

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(
        memory,
        planner_steps=[
            {"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}},
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
    )
    result = orch.run_task("open x.com")

    assert result["status"] == "done"
    planner.next_step.assert_called()
    memory.record_task.assert_called_once_with("open x.com", result["history"], "done", edited=False)


def test_replay_gate_denial_falls_back_to_fresh_planning():
    memory = MagicMock()
    replayed_step = {"action": "click", "description": "star repo", "target_type": "web", "params": {"selector": "#star"}}
    episode = MagicMock(id=2, steps=[replayed_step])
    memory.find_replay.return_value = episode

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(
        memory,
        planner_steps=[
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
    )
    gate.request_approval.return_value = GateDecision(verdict="denied")

    result = orch.run_task("star the repo")

    # Replay step was denied and never executed; fresh planning took over
    # and completed the task via a plain "done" step.
    action_router.execute.assert_not_called()
    assert result["status"] == "done"
    planner.next_step.assert_called()


def test_replay_execution_error_falls_back_to_fresh_planning():
    memory = MagicMock()
    replayed_step = {"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}}
    episode = MagicMock(id=3, steps=[replayed_step])
    memory.find_replay.return_value = episode

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(
        memory,
        planner_steps=[
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
    )
    action_router.execute.side_effect = [RuntimeError("boom")]

    result = orch.run_task("open x.com")

    assert result["status"] == "done"
    planner.next_step.assert_called()


def test_no_memory_configured_behaves_like_phase_two():
    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(
        None,
        planner_steps=[
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
    )
    result = orch.run_task("do something")
    assert result["status"] == "done"


def test_edited_step_during_fresh_planning_calls_review_and_learn_and_flags_edited():
    memory = MagicMock()
    memory.find_replay.return_value = None
    replanner = MagicMock()

    original_step = {"action": "click", "description": "star repo", "target_type": "web",
                      "params": {"selector": "#star"}}
    edited_step = {"action": "click", "description": "star repo (edited)", "target_type": "web",
                    "params": {"selector": "#star-alt"}}

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(
        memory,
        planner_steps=[
            original_step,
            {"action": "done", "description": "finished", "target_type": "web", "params": {}},
        ],
    )
    orch._replanner = replanner
    gate.request_approval.return_value = GateDecision(verdict="approved", edited_step=edited_step)

    result = orch.run_task("star the repo")

    assert result["status"] == "done"
    action_router.execute.assert_called_once_with(edited_step)
    replanner.review_and_learn.assert_called_once_with(
        "star the repo", original_step, edited_step, memory=memory
    )
    memory.record_task.assert_called_once_with("star the repo", result["history"], "done", edited=True)


def test_edited_step_during_replay_flags_edited_and_learns():
    memory = MagicMock()
    replanner = MagicMock()

    original_step = {"action": "click", "description": "star repo", "target_type": "web",
                      "params": {"selector": "#star"}}
    edited_step = {"action": "click", "description": "star repo (edited)", "target_type": "web",
                    "params": {"selector": "#star-alt"}}
    episode = MagicMock(id=9, steps=[original_step])
    memory.find_replay.return_value = episode

    orch, action_router, gate, planner, logger = make_orchestrator_with_memory(memory)
    orch._replanner = replanner
    gate.request_approval.return_value = GateDecision(verdict="approved", edited_step=edited_step)

    result = orch.run_task("star the repo")

    assert result["status"] == "done"
    action_router.execute.assert_called_once_with(edited_step)
    replanner.review_and_learn.assert_called_once_with(
        "star the repo", original_step, edited_step, memory=memory
    )
    memory.record_task.assert_called_once_with("star the repo", result["history"], "done", edited=True)
