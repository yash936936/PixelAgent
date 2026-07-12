import tempfile
from pathlib import Path

import pytest

from src.memory.semantic_store import SemanticStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp:
        s = SemanticStore(Path(tmp) / "semantic.db")
        yield s
        s.close()


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
