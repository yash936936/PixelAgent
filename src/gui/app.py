"""
GUI entry point. Run as:
    python -m src.gui.app
Loads config exactly like src/main.py does (same .env, same GEMINI_API_KEY
requirement) — the GUI is an alternate front-end to the same Orchestrator,
not a separate codepath. See docs/DESIGN.md for the visual system this
window is built from.

Fix for a real gap (Phase 11, docs/DECISIONS.md 2026-08-02): config.load()
previously ran before QApplication was even constructed, so a fresh
install with no .env file crashed with a raw RuntimeError traceback
before any window ever appeared -- directly contradicting Phase 11's own
success criterion ("someone who isn't the author can download one file,
install it, and get to a working first task with no terminal/source
access"). Now checks setup_wizard_logic.needs_setup() first and shows
SetupWizard if so, retrying config.load() only after it completes.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src import config
from src.gui import style
from src.gui.main_window import MainWindow
from src.gui.setup_wizard_logic import needs_setup
from src.gui.widgets.setup_wizard import SetupWizard


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(style.build_stylesheet())

    env_path = Path(".env")
    if needs_setup(env_path):
        wizard = SetupWizard(env_path=env_path)
        if wizard.exec() != SetupWizard.DialogCode.Accepted:
            # User closed/cancelled the wizard -- exit cleanly rather than
            # falling through to config.load(), which would just raise
            # the same unhelpful RuntimeError this wizard exists to avoid.
            return 0

    cfg = config.load(str(env_path))

    window = MainWindow(cfg)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
