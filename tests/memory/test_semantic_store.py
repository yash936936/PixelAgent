import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.memory.semantic_store import SemanticStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp:
        s = SemanticStore(Path(tmp) / "semantic.db")
        yield s
        s.close()


def _install_fake_win32crypt(monkeypatch):
    fake_module = MagicMock()
    fake_module.CryptProtectData.side_effect = lambda data, *a: data[::-1]
    fake_module.CryptUnprotectData.side_effect = lambda data, *a: (None, data[::-1])
    monkeypatch.setitem(sys.modules, "win32crypt", fake_module)


def test_stored_facts_are_actually_encrypted_at_rest_when_dpapi_available(tmp_path, monkeypatch):
    """Phase 8 (docs/DECISIONS.md 2026-08-02): proves the raw bytes written
    to disk don't contain the plaintext value when DPAPI is available --
    not just that at_rest.py's own round-trip works in isolation."""
    from src.memory import semantic_store as semantic_store_module

    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(semantic_store_module.at_rest, "is_available", lambda: True)

    db_path = tmp_path / "encrypted_semantic.db"
    store = SemanticStore(db_path)
    try:
        store.set_fact("github.com", "cookie_banner_selector", "#accept-a-very-specific-selector")
    finally:
        store.close()

    raw_conn = sqlite3.connect(str(db_path))
    row = raw_conn.execute("SELECT value_json FROM facts").fetchone()
    raw_conn.close()
    assert "accept-a-very-specific-selector" not in row[0]


def test_encrypted_semantic_store_still_readable_through_the_normal_api(tmp_path, monkeypatch):
    from src.memory import semantic_store as semantic_store_module

    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(semantic_store_module.at_rest, "is_available", lambda: True)

    store = SemanticStore(tmp_path / "encrypted_semantic.db")
    try:
        store.set_fact("github.com", "cookie_banner_selector", "#accept")
        result = store.get_fact("github.com", "cookie_banner_selector")
    finally:
        store.close()
    assert result == "#accept"


def test_set_and_get_fact(store):
    store.set_fact("github.com", "cookie_banner_selector", "#accept")
    assert store.get_fact("github.com", "cookie_banner_selector") == "#accept"


def test_get_fact_missing_returns_default(store):
    assert store.get_fact("github.com", "missing_key", default="fallback") == "fallback"


def test_set_fact_overwrites_existing(store):
    store.set_fact("github.com", "key", "v1")
    store.set_fact("github.com", "key", "v2")
    assert store.get_fact("github.com", "key") == "v2"


def test_namespaces_do_not_collide(store):
    store.set_fact("github.com", "selector", "#a")
    store.set_fact("gitlab.com", "selector", "#b")
    assert store.get_fact("github.com", "selector") == "#a"
    assert store.get_fact("gitlab.com", "selector") == "#b"


def test_all_facts_returns_full_namespace(store):
    store.set_fact("github.com", "a", 1)
    store.set_fact("github.com", "b", 2)
    assert store.all_facts("github.com") == {"a": 1, "b": 2}


def test_delete_fact(store):
    store.set_fact("github.com", "a", 1)
    store.delete_fact("github.com", "a")
    assert store.get_fact("github.com", "a") is None


def test_preferences_convenience_wrappers(store):
    store.set_preference("default_chrome_profile", "Work")
    assert store.get_preference("default_chrome_profile") == "Work"
    # Preferences live in a reserved namespace, separate from site quirks.
    assert store.get_fact("github.com", "default_chrome_profile") is None


def test_complex_values_roundtrip(store):
    store.set_fact("app.example", "layout", {"nested": [1, 2, 3]})
    assert store.get_fact("app.example", "layout") == {"nested": [1, 2, 3]}


def test_all_preferences_returns_reserved_namespace_only(store):
    # Added for the GUI memory browser (src/gui/widgets/memory_panel.py) —
    # must go through a public method rather than reaching into the
    # namespace constant/private state directly.
    store.set_preference("default_chrome_profile", "Work")
    store.set_preference("max_steps", 40)
    store.set_fact("github.com", "cookie_banner_selector", "#accept")

    prefs = store.all_preferences()

    assert prefs == {"default_chrome_profile": "Work", "max_steps": 40}
    assert "cookie_banner_selector" not in prefs
