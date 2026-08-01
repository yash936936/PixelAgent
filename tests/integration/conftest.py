"""
Shared fixtures for the integration test tier.

Why this tier exists: every other test in this repo (232 of them as of the
last review pass) exercises OCREngine, element_detector, and screen_diff
against synthetic in-memory data -- hand-built OCRWord lists or solid-color
PIL images. That's fast and deterministic, but it has never actually
proven that real Tesseract output on a real rendered page produces
bounding boxes element_detector can classify correctly, or that
screen_diff's 0.01 change_ratio threshold is well-calibrated against real
rendering noise (anti-aliasing, animation, font hinting) rather than only
the hand-crafted solid-color cases in tests/perception/test_screen_diff.py.

This tier closes that gap using real local HTML fixture pages (no network
needed -- see tests/integration/fixtures/pages/) rendered by a real
headless Chromium via Playwright, feeding real screenshots through the
actual OCREngine (real Tesseract binary, not mocked) and real
screen_diff.compare(). This is still not the real end-to-end system (no
real OS mouse/keyboard, no real Windows DPI scaling), but it's a
meaningfully closer proxy than fully synthetic data, and it runs
completely offline and deterministically in CI.

Requires: a working Playwright Chromium install (`playwright install
chromium`) and the Tesseract OCR binary on PATH. If either is missing,
skip this tier the same way tests/gui/ is skipped when PySide6 isn't
installed: `pytest --ignore=tests/integration`.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pages"

# Fixed viewport so pixel coordinates in tests are stable across machines --
# real DPI/scaling variation is a separate, real risk (flagged in review)
# that this fixed-viewport tier deliberately does NOT cover; it only
# proves the OCR/diff pipeline works correctly at one known scale.
_VIEWPORT = {"width": 800, "height": 600}


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture()
def page(browser):
    pg = browser.new_page(viewport=_VIEWPORT)
    yield pg
    pg.close()


def fixture_url(name: str) -> str:
    """file:// URL for one of tests/integration/fixtures/pages/*.html --
    no network access, no test server needed."""
    path = (_FIXTURES_DIR / name).resolve()
    if not path.exists():
        raise FileNotFoundError(f"No such fixture page: {path}")
    return f"file://{path}"
