"""
Full dashboard main window: task composer + live trace + memory browser +
LoopAudit stats, per the user's requested first GUI scope. Assembled from
docs/DESIGN.md's mapped components — see that file's "Components" table for
which Steep component backs each panel.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.gui import style
from src.gui.widgets.confirmation_dialog import ConfirmationDialog
from src.gui.widgets.memory_panel import MemoryPanel
from src.gui.widgets.stats_panel import StatsPanel
from src.gui.widgets.task_composer import TaskComposer
from src.gui.widgets.trace_panel import TracePanel
from src.gui.worker import GateBridge, TaskWorker
from src.memory.memory_api import MemoryAPI


class MainWindow(QWidget):
    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._worker: TaskWorker | None = None

        self.setObjectName("dashboardRoot")
        self.setWindowTitle("Pixel — Dashboard")
        self.resize(1100, 720)

        self._gate_bridge = GateBridge()
        self._gate_bridge.request_confirmation.connect(
            self._on_confirmation_requested, Qt.BlockingQueuedConnection
        )

        # Own MemoryAPI instance just for browsing — the task run creates
        # its own instance inside TaskWorker (a fresh SQLite connection per
        # thread, since sqlite3 connections aren't safely shared across
        # threads). Both point at the same on-disk DB files under
        # cfg.log_dir, so refresh() after a run picks up what the run wrote.
        self._browse_memory = MemoryAPI(log_dir=cfg.log_dir)

        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            style.SPACING[24], style.SPACING[24], style.SPACING[24], style.SPACING[24]
        )
        outer.setSpacing(style.SPACING[20])

        title = QLabel("Pixel")
        title.setProperty("role", "heading")
        outer.addWidget(title)

        self._composer = TaskComposer()
        self._composer.run_requested.connect(self._start_task)
        outer.addWidget(self._composer)

        self._status_label = QLabel("Idle.")
        self._status_label.setProperty("role", "caption")
        outer.addWidget(self._status_label)

        splitter = QSplitter(Qt.Horizontal)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(style.SPACING[20])
        self._trace_panel = TracePanel()
        self._stats_panel = StatsPanel()
        left_layout.addWidget(self._trace_panel, stretch=3)
        left_layout.addWidget(self._stats_panel, stretch=1)

        self._memory_panel = MemoryPanel(self._browse_memory)

        splitter.addWidget(left_col)
        splitter.addWidget(self._memory_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        outer.addWidget(splitter, stretch=1)

    def _start_task(self, instruction: str) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._trace_panel.clear()
        self._stats_panel.reset()
        self._status_label.setText(f'Running: "{instruction}"')
        self._composer.set_running(True)

        self._worker = TaskWorker(instruction, self._cfg, self._gate_bridge)
        self._worker.step_logged.connect(self._on_step_logged)
        self._worker.gate_logged.connect(self._trace_panel.add_gate_decision)
        self._worker.task_finished.connect(self._on_task_finished)
        self._worker.task_failed.connect(self._on_task_failed)
        self._worker.start()

    def _on_step_logged(self, record: dict) -> None:
        self._trace_panel.add_step(record)
        self._stats_panel.update_from_audit(record.get("audit", {}))

    def _on_task_finished(self, result: dict) -> None:
        self._trace_panel.add_task_complete(result)
        self._status_label.setText(f"Finished: {result.get('status')}")
        self._composer.set_running(False)
        self._browse_memory.close()
        self._browse_memory = MemoryAPI(log_dir=self._cfg.log_dir)
        self._memory_panel._memory = self._browse_memory
        self._memory_panel.refresh()

    def _on_task_failed(self, message: str) -> None:
        self._status_label.setText(f"Error: {message}")
        self._composer.set_running(False)
        QMessageBox.critical(self, "Task failed", message)

    def _on_confirmation_requested(self, step: dict, risk_value: str, context) -> None:
        dialog = ConfirmationDialog(step, risk_value, context, parent=self)
        dialog.exec()
        self._gate_bridge.set_pending_decision(dialog.decision)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt override naming
        self._browse_memory.close()
        super().closeEvent(event)
