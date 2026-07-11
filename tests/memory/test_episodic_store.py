import tempfile
from pathlib import Path

import pytest

from src.memory.episodic_store import EpisodicStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp:
        s = EpisodicStore(Path(tmp) / "episodic.db")
        yield s
        s.close()


def _history(steps):
    return [{"step": s, "outcome": {"status": "executed"}} for s in steps]


def test_record_and_find_exact_match(store):
    steps = [{"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}}]
    store.record("Open x.com", _history(steps), "done")

    episode = store.find_match("open x.com")
    assert episode is not None
    assert episode.steps == steps


def test_find_match_returns_none_when_no_similar_task(store):
    steps = [{"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}}]
    store.record("Open x.com", _history(steps), "done")

    assert store.find_match("book a flight to Tokyo") is None


def test_non_replayable_status_never_matched(store):
    steps = [{"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}}]
    store.record("Open x.com", _history(steps), "error")

    assert store.find_match("open x.com") is None


def test_empty_steps_never_matched(store):
    store.record("do nothing task", [], "done")
    assert store.find_match("do nothing task") is None


def test_most_recent_best_match_wins(store):
    old_steps = [{"action": "click", "description": "old", "target_type": "web", "params": {}}]
    new_steps = [{"action": "click", "description": "new", "target_type": "web", "params": {}}]
    store.record("star the repo", _history(old_steps), "done")
    store.record("star the repo", _history(new_steps), "done")

    episode = store.find_match("star the repo")
    assert episode.steps == new_steps


def test_all_episodes_includes_non_replayable(store):
    store.record("task a", [], "done")
    store.record("task b", [], "error")
    episodes = store.all_episodes()
    assert len(episodes) == 2
