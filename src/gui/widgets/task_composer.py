"""
The task-instruction input box — Steep's "Input / Composer" component
(docs/DESIGN.md). Emits run_requested(text) when the user submits.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.gui import style


class TaskComposer(QWidget):
    run_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(style.SPACING[8])

        row = QHBoxLayout()
        row.setSpacing(style.SPACING[12])

        self._input = QLineEdit()
        self._input.setPlaceholderText("What should Pixel do?")
        self._input.setProperty("variant", "composer")
        self._input.returnPressed.connect(self._emit_run)
        row.addWidget(self._input, stretch=1)

        self._run_btn = QPushButton("Run task")
        self._run_btn.setProperty("variant", "filled")
        self._run_btn.clicked.connect(self._emit_run)
        row.addWidget(self._run_btn)

        layout.addLayout(row)

    def _emit_run(self) -> None:
        text = self._input.text().strip()
        if text:
            self.run_requested.emit(text)

    def set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._run_btn.setText("Running…" if running else "Run task")
        self._input.setEnabled(not running)
