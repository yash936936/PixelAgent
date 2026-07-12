"""
LoopAudit stats — Steep's "Stat Card with Chart" component, simplified to
the numbers only (no chart yet; see docs/DESIGN.md's mapping table). Reflects
src/observability/logger.py's LoopAudit: step_count and llm_calls. Cost is
intentionally not shown here (removed per user request) — it's still tracked
internally by LoopAudit/Logger for the trace log, just not surfaced in this
panel.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.gui import style


class StatCard(QFrame):
    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", "floating")
        self.setStyleSheet(style.risk_card_qss("done"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self._value_label = QLabel("0")
        self._value_label.setStyleSheet(f"background: transparent; font-size: 20px; font-weight: 500; color: {style.INK_BLACK};")
        layout.addWidget(self._value_label)

        caption = QLabel(label)
        caption.setStyleSheet(f"background: transparent; font-size: 13px; color: {style.SLATE_GRAY};")
        layout.addWidget(caption)

    def set_value(self, value) -> None:
        self._value_label.setText(str(value))


class StatsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        heading = QLabel("Loop audit")
        heading.setProperty("role", "heading")
        outer.addWidget(heading)

        row = QHBoxLayout()
        row.setSpacing(style.SPACING[16])
        self._steps_card = StatCard("Steps")
        self._llm_card = StatCard("LLM calls")
        row.addWidget(self._steps_card)
        row.addWidget(self._llm_card)
        outer.addLayout(row)
        outer.addStretch()

    def update_from_audit(self, audit: dict) -> None:
        self._steps_card.set_value(audit.get("step_count", 0))
        self._llm_card.set_value(audit.get("llm_calls", 0))

    def reset(self) -> None:
        self.update_from_audit({})
