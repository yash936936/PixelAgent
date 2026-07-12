"""
Memory browser: episodic task history (src/memory/episodic_store.py) and
semantic preferences/quirks (src/memory/semantic_store.py), read via
MemoryAPI so this widget never touches SQLite directly — same rule
memory_api.py enforces for orchestrator.py/planner.py. Read-only for now;
editing facts from the GUI is a reasonable future addition, not built here.
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QTabWidget, QVBoxLayout, QWidget

from src.gui import style
from src.memory.memory_api import MemoryAPI


class MemoryPanel(QWidget):
    def __init__(self, memory: MemoryAPI, parent=None) -> None:
        super().__init__(parent)
        self._memory = memory

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Memory")
        heading.setProperty("role", "heading")
        outer.addWidget(heading)

        tabs = QTabWidget()

        self._episodic_list = QListWidget()
        tabs.addTab(self._episodic_list, "Task history")

        self._flagged_list = QListWidget()
        tabs.addTab(self._flagged_list, "Flagged for review")

        self._prefs_list = QListWidget()
        tabs.addTab(self._prefs_list, "Preferences")

        outer.addWidget(tabs)
        self.refresh()

    def refresh(self) -> None:
        self._episodic_list.clear()
        for ep in self._memory.all_episodes():
            when = datetime.fromtimestamp(ep.created_at).strftime("%Y-%m-%d %H:%M")
            text = f"[{ep.status}] {ep.instruction}  ({when})"
            item = QListWidgetItem(text)
            item.setForeground(_status_color(ep.status))
            self._episodic_list.addItem(item)

        self._flagged_list.clear()
        for ep in self._memory.flagged_for_review():
            when = datetime.fromtimestamp(ep.created_at).strftime("%Y-%m-%d %H:%M")
            edited = " (edited)" if ep.edited else ""
            self._flagged_list.addItem(f"[{ep.status}]{edited} {ep.instruction}  ({when})")

        self._prefs_list.clear()
        prefs = self._memory.all_preferences()
        if not prefs:
            self._prefs_list.addItem("(no preferences recorded yet)")
        for key, value in prefs.items():
            self._prefs_list.addItem(f"{key} = {value}")


def _status_color(status: str):
    from PySide6.QtGui import QColor

    if status == "done":
        return QColor(style.INK_BLACK)
    return QColor(style.SIENNA_BROWN)
