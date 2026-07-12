"""
Modal confirmation dialog — the GUI equivalent of console_prompt.py, matching
the layout in docs/DESIGN.md "Confirmation prompt layout". Implements the
same prompt_fn(step, risk, context) -> GateDecision contract as
console_prompt, so it can be passed straight to ConfirmationGate.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.gui import style


class ConfirmationDialog(QDialog):
    """risk_key: "external" or "destructive" (Local never reaches the gate,
    per gate.py). step is the raw step dict; context is a GateContext or
    None. After exec(), read .verdict / .edited_step / .raw_user_input."""

    def __init__(self, step: dict, risk_key: str, context=None, parent=None) -> None:
        super().__init__(parent)
        self._step = step
        self._risk_key = risk_key
        self._context = context

        self.verdict: str = "denied"
        self.edited_step: dict | None = None
        self.raw_user_input: str | None = None

        self.setWindowTitle("Pixel — Approval needed")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setStyleSheet(
            f"QDialog {{ {style.risk_card_qss(risk_key)} }} "
            f"QDialog QLabel {{ background: transparent; }}"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        rs = style.RISK_STYLE[self._risk_key]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        tag = QLabel(rs["label"])
        tag.setStyleSheet(f"font-size: 13px; font-weight: 500; color: {rs['ink']};")
        layout.addWidget(tag)

        description = self._step.get("description", self._step.get("action", "(no description)"))
        action_label = QLabel(description)
        action_label.setWordWrap(True)
        action_label.setStyleSheet(f"font-size: 17px; color: {rs['ink']};")
        layout.addWidget(action_label)

        raw = QLabel(f"Action: {self._step.get('action')}   params={self._step.get('params', {})}")
        raw.setWordWrap(True)
        raw.setStyleSheet(f"font-size: 13px; color: {style.SLATE_GRAY};")
        layout.addWidget(raw)

        profile = getattr(self._context, "account_profile", None) or "not available"
        screenshot = getattr(self._context, "screenshot_path", None) or "not available"
        meta = QLabel(f"Account/profile: {profile}\nScreenshot: {screenshot}")
        meta.setStyleSheet(f"font-size: 13px; color: {style.SLATE_GRAY};")
        layout.addWidget(meta)

        self._edit_box = QTextEdit()
        self._edit_box.setPlaceholderText("Edit description before approving (optional)")
        self._edit_box.setFixedHeight(60)
        self._edit_box.setProperty("variant", "composer")
        self._edit_box.setVisible(False)
        self._edit_mode = False  # explicit flag — Qt's isVisible() reflects
        # actual on-screen visibility (which depends on the whole window
        # being shown), not just this widget's own setVisible() call, so it
        # can't be used to detect "user chose to edit" reliably before the
        # dialog has actually been exec()'d/shown. Caught by
        # tests/gui/test_confirmation_dialog.py's edit-box test.
        layout.addWidget(self._edit_box)

        self._confirm_input: QLineEdit | None = None
        if self._risk_key == "destructive":
            self._confirm_input = QLineEdit()
            self._confirm_input.setPlaceholderText('Type "CONFIRM" to proceed')
            self._confirm_input.setProperty("variant", "composer")
            layout.addWidget(self._confirm_input)

        button_row = QHBoxLayout()
        approve_btn = QPushButton("Approve")
        approve_btn.setProperty("variant", "filled")
        approve_btn.clicked.connect(self._on_approve)

        deny_btn = QPushButton("Deny")
        deny_btn.setProperty("variant", "ghost")
        deny_btn.clicked.connect(self._on_deny)

        edit_btn = QPushButton("Edit")
        edit_btn.setProperty("variant", "ghost")
        edit_btn.clicked.connect(self._toggle_edit)

        button_row.addWidget(deny_btn)
        button_row.addWidget(edit_btn)
        button_row.addStretch()
        button_row.addWidget(approve_btn)
        layout.addLayout(button_row)

    def _toggle_edit(self) -> None:
        self._edit_mode = not self._edit_mode
        self._edit_box.setVisible(self._edit_mode)

    def _on_deny(self) -> None:
        self.verdict = "denied"
        self.reject()

    def _on_approve(self) -> None:
        self.verdict = "approved"
        if self._edit_mode and self._edit_box.toPlainText().strip():
            self.edited_step = dict(self._step)
            self.edited_step["description"] = self._edit_box.toPlainText().strip()
        if self._confirm_input is not None:
            self.raw_user_input = self._confirm_input.text().strip()
        self.accept()

    @property
    def decision(self):
        # Local import to avoid a hard PySide6 dependency in gate.py/planner
        # code that doesn't otherwise need Qt.
        from src.confirmation.gate import GateDecision

        return GateDecision(
            verdict=self.verdict, edited_step=self.edited_step, raw_user_input=self.raw_user_input
        )
