"""
Live trace panel: one entry per executed step or gate decision, appended as
the task runs. Each entry is a Neutral Card (Local) or risk-colored card
(External/Destructive), per docs/DESIGN.md's Risk-State Mapping.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from src.gui import style


class TracePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Live trace")
        heading.setProperty("role", "heading")
        outer.addWidget(heading)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border: none;")

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setSpacing(style.SPACING[8])
        self._list_layout.addStretch()
        self._scroll.setWidget(self._container)

        outer.addWidget(self._scroll)

    def clear(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_step(self, record: dict) -> None:
        risk_key = record.get("risk") or "local"
        outcome = record.get("outcome", {})
        status = outcome.get("status", "executed")
        if status == "error":
            risk_key = "error"
        card = self._make_card(
            risk_key,
            title=f"Step {record['step_num']}: {record['step'].get('description', record['step'].get('action'))}",
            subtitle=f"status: {status}",
        )
        self._list_layout.insertWidget(self._list_layout.count() - 1, card)
        self._scroll_to_bottom()

    def add_gate_decision(self, record: dict) -> None:
        card = self._make_card(
            record["risk"],
            title=f"Step {record['step_num']} gate: {record['verdict'].upper()}"
            + (" (edited)" if record.get("edited") else ""),
            subtitle=record["step"].get("description", record["step"].get("action", "")),
        )
        self._list_layout.insertWidget(self._list_layout.count() - 1, card)
        self._scroll_to_bottom()

    def add_task_complete(self, result: dict) -> None:
        risk_key = "done" if result.get("status") == "done" else "error"
        card = self._make_card(
            risk_key,
            title=f"Task finished: {result.get('status')}",
            subtitle=result.get("instruction", ""),
        )
        self._list_layout.insertWidget(self._list_layout.count() - 1, card)
        self._scroll_to_bottom()

    def _make_card(self, risk_key: str, title: str, subtitle: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(style.risk_card_qss(risk_key))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("background: transparent; font-size: 15px; font-weight: 500;")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet(f"background: transparent; font-size: 13px; color: {style.SLATE_GRAY};")
            layout.addWidget(subtitle_label)

        return frame

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
