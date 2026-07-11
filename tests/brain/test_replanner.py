from unittest.mock import MagicMock

import pytest

from src.brain.replanner import ReplanExhausted, Replanner


def test_correct_calls_planner_with_correction_note():
    planner = MagicMock()
    planner.next_step.return_value = {"action": "click", "description": "corrected"}
    replanner = Replanner(planner=planner, max_retries=2)

    failed_step = {"action": "click", "params": {"selector": "#missing"}}
    result = replanner.correct("do the thing", failed_step, {"url": "x"}, [], attempt=1)

    assert result["description"] == "corrected"
    planner.next_step.assert_called_once()
    _, _, corrected_history = planner.next_step.call_args[0]
    assert corrected_history[-1]["step"] == failed_step
    assert corrected_history[-1]["outcome"]["status"] == "unexpected_screen_state"


def test_correct_raises_when_retries_exhausted():
    planner = MagicMock()
    replanner = Replanner(planner=planner, max_retries=2)

    with pytest.raises(ReplanExhausted):
        replanner.correct("do the thing", {"action": "click"}, {}, [], attempt=3)

    planner.next_step.assert_not_called()


def test_review_and_learn_noop_without_memory():
    replanner = Replanner(planner=MagicMock())
    # Should not raise even though memory is None (memory disabled at runtime).
    original = {"action": "click", "params": {"selector": "#star"}}
    edited = {"action": "click", "params": {"selector": "#star-alt"}}
    replanner.review_and_learn("star the repo", original, edited, memory=None)


def test_review_and_learn_noop_when_step_unchanged():
    replanner = Replanner(planner=MagicMock())
    memory = MagicMock()
    step = {"action": "click", "params": {"selector": "#star"}}

    replanner.review_and_learn("star the repo", step, step, memory=memory)

    memory.set_site_quirk.assert_not_called()


def test_review_and_learn_writes_correction_when_step_edited():
    replanner = Replanner(planner=MagicMock())
    memory = MagicMock()
    original = {"action": "click", "params": {"selector": "#star"}}
    edited = {"action": "click", "params": {"selector": "#star-alt"}}

    replanner.review_and_learn("star the repo", original, edited, memory=memory)

    memory.set_site_quirk.assert_called_once_with(
        "corrections:click",
        "#star",
        {"instruction": "star the repo", "original_step": original, "edited_step": edited},
    )
