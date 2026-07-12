import tempfile
from pathlib import Path

from src.gui.widgets.memory_panel import MemoryPanel
from src.memory.memory_api import MemoryAPI


def _memory():
    return MemoryAPI(log_dir=Path(tempfile.mkdtemp()))


def test_empty_memory_shows_no_data_placeholder(qapp):
    mem = _memory()
    panel = MemoryPanel(mem)
    assert panel._episodic_list.count() == 0
    assert panel._prefs_list.count() == 1  # "(no preferences recorded yet)"
    mem.close()


def test_recorded_task_appears_in_episodic_list(qapp):
    mem = _memory()
    mem.record_task("star the repo", [{"step": {"action": "click"}, "outcome": {}}], "done")
    panel = MemoryPanel(mem)
    assert panel._episodic_list.count() == 1
    assert "star the repo" in panel._episodic_list.item(0).text()
    mem.close()


def test_flagged_task_appears_in_flagged_list(qapp):
    mem = _memory()
    mem.record_task("failed task", [{"step": {"action": "click"}, "outcome": {}}], "error")
    panel = MemoryPanel(mem)
    assert panel._flagged_list.count() == 1
    mem.close()


def test_preference_appears_in_prefs_list(qapp):
    mem = _memory()
    mem.set_preference("default_chrome_profile", "Work")
    panel = MemoryPanel(mem)
    assert panel._prefs_list.count() == 1
    assert "default_chrome_profile" in panel._prefs_list.item(0).text()
    mem.close()


def test_refresh_picks_up_new_data(qapp):
    mem = _memory()
    panel = MemoryPanel(mem)
    assert panel._episodic_list.count() == 0
    mem.record_task("new task", [{"step": {"action": "click"}, "outcome": {}}], "done")
    panel.refresh()
    assert panel._episodic_list.count() == 1
    mem.close()
