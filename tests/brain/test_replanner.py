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


def test_review_and_learn_noop_without_semantic_store():
    replanner = Replanner(planner=MagicMock())
    # Should not raise even though semantic_store is None (Phase 3 dependency
    # doesn't exist yet).
    replanner.review_and_learn({"user_edit": "changed selector"}, semantic_store=None)


def test_review_and_learn_writes_fact_when_store_present():
    replanner = Replanner(planner=MagicMock())
    semantic_store = MagicMock()

    replanner.review_and_learn(
        {"task_type": "star_repo", "user_edit": "used different repo"}, semantic_store=semantic_store
    )

    semantic_store.write_fact.assert_called_once_with(
        subject="star_repo", fact={"correction": "used different repo"}
    )
