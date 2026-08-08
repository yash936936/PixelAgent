"""
First-run setup wizard (Phase 11, docs/DECISIONS.md 2026-08-02). Shown by
src/gui/app.py BEFORE config.load() is ever attempted, when
setup_wizard_logic.needs_setup() detects no usable .env exists yet.
Collects the Gemini API key (required), default Chrome profile and
profiles directory (optional, sensible defaults apply), and requires an
explicit acknowledgement of what Pixel can actually do before "Get
Started" is enabled -- the "permissions explanation" Phase 11 calls for.

All business logic (validation, writing the .env file) lives in
setup_wizard_logic.py, imported here with zero duplication -- this class
is UI plumbing only, matching this project's existing GateBridge/
prompt_fn separation of concerns.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.gui import style
from src.gui.setup_wizard_logic import looks_like_a_real_api_key, write_env_file


class SetupWizard(QDialog):
    def __init__(self, env_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._env_path = env_path
        self.setWindowTitle("Welcome to Pixel — first-time setup")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(style.SPACING[16])
        layout.setContentsMargins(
            style.SPACING[24], style.SPACING[24], style.SPACING[24], style.SPACING[24]
        )

        intro = QLabel(
            "Pixel needs a Gemini API key to plan tasks. Get a free key at "
            "<a href='https://aistudio.google.com/apikey'>aistudio.google.com/apikey</a>."
        )
        intro.setOpenExternalLinks(True)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        layout.addWidget(QLabel("Gemini API key"))
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("AQ....")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.textChanged.connect(self._update_start_button_state)
        layout.addWidget(self._api_key_input)

        layout.addWidget(QLabel("Default Chrome profile (optional — leave as \"Default\" if unsure)"))
        self._profile_input = QLineEdit()
        self._profile_input.setPlaceholderText("Default")
        layout.addWidget(self._profile_input)

        layout.addWidget(
            QLabel("Chrome profiles directory (optional — leave blank to use ./profiles)")
        )
        self._profiles_dir_input = QLineEdit()
        self._profiles_dir_input.setPlaceholderText(r"C:\Users\you\AppData\Local\Google\Chrome\User Data")
        layout.addWidget(self._profiles_dir_input)

        # Permissions explanation + explicit consent (Phase 11's own
        # requirement) -- Get Started stays disabled until both this is
        # checked AND a plausible-looking API key is entered.
        consent_text = QLabel(
            "Pixel will control your mouse, keyboard, and a real Chrome browser profile to carry "
            "out the tasks you give it. Anything External-risk or Destructive requires your explicit "
            "approval before it happens — see the confirmation prompts once you start a task."
        )
        consent_text.setWordWrap(True)
        layout.addWidget(consent_text)

        self._consent_checkbox = QCheckBox("I understand and want to proceed")
        self._consent_checkbox.stateChanged.connect(self._update_start_button_state)
        layout.addWidget(self._consent_checkbox)

        self._start_button = QPushButton("Get Started")
        self._start_button.setProperty("variant", "filled")
        self._start_button.setEnabled(False)
        self._start_button.clicked.connect(self._on_start)
        layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignRight)

    def _update_start_button_state(self) -> None:
        api_key_ok = looks_like_a_real_api_key(self._api_key_input.text())
        self._start_button.setEnabled(api_key_ok and self._consent_checkbox.isChecked())

    def _on_start(self) -> None:
        api_key = self._api_key_input.text().strip()
        if not looks_like_a_real_api_key(api_key):
            QMessageBox.warning(
                self, "Check your API key",
                "That doesn't look like a valid Gemini API key. Get one at "
                "https://aistudio.google.com/apikey and paste it here.",
            )
            return

        write_env_file(
            self._env_path,
            gemini_api_key=api_key,
            default_chrome_profile=self._profile_input.text().strip() or "Default",
            profiles_dir=self._profiles_dir_input.text().strip(),
        )
        self.accept()
