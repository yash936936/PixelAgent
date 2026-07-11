import tempfile
from pathlib import Path

import pytest

from src.memory.memory_api import MemoryAPI


@pytest.fixture
def memory():
    with tempfile.TemporaryDirectory() as tmp:
        api = MemoryAPI(log_dir=Path(tmp))
        yield api
        api.close()


def test_record_and_find_replay(memory):
    history = [
        {"step": {"action": "navigate", "description": "go", "target_type": "web", "params": {"url": "x.com"}},
         "outcome": {"status": "executed"}}
    ]
    memory.record_task("open x.com", history, "done")

    episode = memory.find_replay("open x.com")
    assert episode is not None
    assert episode.steps[0]["action"] == "navigate"


def test_find_replay_none_for_unmatched(memory):
    assert memory.find_replay("some never-before-seen instruction") is None


def test_preferences_roundtrip(memory):
    memory.set_preference("default_chrome_profile", "Work")
    assert memory.get_preference("default_chrome_profile") == "Work"
    assert memory.get_preference("missing", default="x") == "x"


def test_site_quirks_roundtrip(memory):
    memory.set_site_quirk("github.com", "cookie_banner_selector", "#accept")
    assert memory.get_site_quirk("github.com", "cookie_banner_selector") == "#accept"
    assert memory.get_site_quirk("gitlab.com", "cookie_banner_selector") is None


def test_all_episodes(memory):
    memory.record_task("task one", [], "done")
    memory.record_task("task two", [], "error")
    assert len(memory.all_episodes()) == 2
