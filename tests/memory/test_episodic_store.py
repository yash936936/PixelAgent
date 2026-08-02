import json
import tempfile
import time
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


def test_find_match_reports_match_score(store):
    steps = [{"action": "navigate", "description": "go", "target_type": "web", "params": {}}]
    store.record("open github and star the repo", _history(steps), "done")
    match = store.find_match("open github and star the repo")
    assert match is not None
    assert match.match_score == pytest.approx(1.0)


def test_find_match_score_reflects_partial_similarity(store):
    steps = [{"action": "navigate", "description": "go", "target_type": "web", "params": {}}]
    store.record("open github.com and click star", _history(steps), "done")
    match = store.find_match("open github.com and click the star button")
    assert match is not None
    assert 0.82 <= match.match_score < 1.0


def test_old_schema_version_episode_is_never_replayed(store, monkeypatch, tmp_path):
    """Real bug found live on 2026-08-01 (docs/DECISIONS.md): a stale
    episode recorded before the expect_window_contains safety fix was
    replayed verbatim on the next matching task, resurrecting the exact
    bug the fix closed. Simulates recording under an OLDER schema version,
    then confirms find_match() (running under the CURRENT version) refuses
    to replay it."""
    import src.memory.episodic_store as episodic_store_module

    monkeypatch.setattr(episodic_store_module, "STEP_SCHEMA_VERSION", 1)
    steps = [{"action": "type", "target_type": "desktop", "params": {"text": "hello"}}]
    store.record("open notepad and type hello", _history(steps), "done")

    monkeypatch.setattr(episodic_store_module, "STEP_SCHEMA_VERSION", 2)
    assert store.find_match("open notepad and type hello") is None


def test_current_schema_version_episode_is_still_replayed(store):
    """Sanity check the fix above doesn't just break replay entirely --
    an episode recorded under the CURRENT version must still match."""
    steps = [{"action": "type", "target_type": "desktop",
              "params": {"text": "hello", "expect_window_contains": "Notepad"}}]
    store.record("open notepad and type hello", _history(steps), "done")
    match = store.find_match("open notepad and type hello")
    assert match is not None
    assert match.steps == steps


def test_migration_backfills_existing_rows_as_schema_version_1(tmp_path):
    """A database created before this fix has no schema_version column at
    all. The migration must backfill existing rows as version 1 (correct,
    since they predate the fix and cannot be trusted for replay), not
    crash or silently treat them as current-version."""
    import sqlite3

    db_path = tmp_path / "legacy.db"
    # Simulate a pre-fix database: no schema_version column.
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, instruction TEXT NOT NULL, "
        "normalized_instruction TEXT NOT NULL, steps_json TEXT NOT NULL, status TEXT NOT NULL, "
        "edited INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL)"
    )
    conn.execute(
        "INSERT INTO episodes (instruction, normalized_instruction, steps_json, status, edited, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("legacy task", "legacy task", json.dumps([{"action": "click", "target_type": "web", "params": {}}]),
         "done", 0, time.time()),
    )
    conn.commit()
    conn.close()

    store = EpisodicStore(db_path)
    try:
        # Migrated legacy row must never be offered as a replay candidate.
        assert store.find_match("legacy task") is None
    finally:
        store.close()
