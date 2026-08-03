import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

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


def _install_fake_win32crypt(monkeypatch):
    """Same reversible fake used in tests/security/test_at_rest.py --
    exercises the real protect()/unprotect() code path (hex encoding, the
    (description, data) tuple) rather than trusting the module boundary."""
    fake_module = MagicMock()
    fake_module.CryptProtectData.side_effect = lambda data, *a: data[::-1]
    fake_module.CryptUnprotectData.side_effect = lambda data, *a: (None, data[::-1])
    monkeypatch.setitem(sys.modules, "win32crypt", fake_module)


def test_stored_rows_are_actually_encrypted_at_rest_when_dpapi_available(tmp_path, monkeypatch):
    """Phase 8 (docs/DECISIONS.md 2026-08-02): proves encryption isn't just
    implemented in at_rest.py in isolation -- the raw bytes written to disk
    by EpisodicStore itself must not contain the plaintext instruction or
    step content when DPAPI is available."""
    from src.memory import episodic_store as episodic_store_module

    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(episodic_store_module.at_rest, "is_available", lambda: True)

    db_path = tmp_path / "encrypted.db"
    store = EpisodicStore(db_path)
    try:
        store.record(
            "a very specific secret task instruction",
            _history([{"action": "type", "target_type": "web", "params": {"text": "secret-value"}}]),
            "done",
        )
    finally:
        store.close()

    raw_conn = sqlite3.connect(str(db_path))
    row = raw_conn.execute("SELECT instruction, steps_json FROM episodes").fetchone()
    raw_conn.close()

    assert "a very specific secret task instruction" not in row[0]
    assert "secret-value" not in row[1]


def test_encrypted_store_still_replays_correctly_through_the_normal_api(tmp_path, monkeypatch):
    """The whole point of transparent encryption: every existing caller
    (find_match's difflib matching included) keeps working exactly as
    before, with decryption happening automatically on read."""
    from src.memory import episodic_store as episodic_store_module

    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(episodic_store_module.at_rest, "is_available", lambda: True)

    steps = [{"action": "navigate", "target_type": "web", "params": {"url": "https://example.com"}}]
    store = EpisodicStore(tmp_path / "encrypted.db")
    try:
        store.record("open example dot com", _history(steps), "done")
        match = store.find_match("open example dot com")
    finally:
        store.close()

    assert match is not None
    assert match.instruction == "open example dot com"
    assert match.steps == steps
