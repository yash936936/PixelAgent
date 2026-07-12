"""
Shared pytest fixtures for GUI tests. Runs Qt in offscreen mode (no real
display required) — this is what makes these tests runnable in CI/sandboxed
environments, matching how this project's own build environment verified
them (see docs/DECISIONS.md 2026-07-12 GUI entry).
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app
