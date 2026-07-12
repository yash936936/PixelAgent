"""
GUI entry point. Run as:
    python -m src.gui.app
Loads config exactly like src/main.py does (same .env, same GEMINI_API_KEY
requirement) — the GUI is an alternate front-end to the same Orchestrator,
not a separate codepath. See docs/DESIGN.md for the visual system this
window is built from.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src import config
from src.gui import style
from src.gui.main_window import MainWindow


def main() -> int:
    cfg = config.load()

    app = QApplication(sys.argv)
    app.setStyleSheet(style.build_stylesheet())

    window = MainWindow(cfg)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
