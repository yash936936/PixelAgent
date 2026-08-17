"""
Shared helper for tests that exercise the real Tesseract binary (not a mock).

Real bug found live (2026-08-17, docs/DECISIONS.md): tests/integration/test_real_ocr_pipeline.py
and tests/perception/test_ocr_solid_background_regression.py both constructed
`OCREngine()` with no arguments, which leaves pytesseract's `tesseract_cmd`
at its bare default `"tesseract"` -- relying on the binary being on PATH.
That's true in this project's Linux CI (`apt install tesseract-ocr` adds it
to PATH) but is NOT a safe assumption on Windows, where a very common,
supported install pattern (this project's own README/doctor.py included)
is pointing `TESSERACT_CMD` at the binary's full path instead of modifying
PATH. Production code (`src/main.py`, `src/gui/worker.py`) already gets
this right -- both construct `OCREngine(tesseract_cmd=cfg.tesseract_cmd)` --
it was only these two real-Tesseract test files that skipped it.

Use `real_ocr_engine()` instead of `OCREngine()` directly in any test that
calls the real Tesseract binary, so both PATH-based (Linux CI) and
TESSERACT_CMD-based (this project's own documented Windows setup) machines
resolve the same binary a real run would use.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

from src.perception.ocr import OCREngine

# Same as config.py's own load_dotenv() call, but done here directly rather
# than via a full Config.load() -- these OCR-only tests need TESSERACT_CMD
# and nothing else, and Config.load() raises RuntimeError if GEMINI_API_KEY
# isn't set (unset in this project's own CI, since no LLM call is needed
# for these tests), which would break them for an unrelated reason if
# routed through the full config loader. Still needs its own load_dotenv()
# call, though -- nothing else in a plain `pytest` invocation loads .env
# into os.environ on its own, so skipping this would silently miss a real
# TESSERACT_CMD set in the user's own .env file.
load_dotenv()


def real_ocr_engine() -> OCREngine:
    """Builds an OCREngine the same way production code resolves
    tesseract_cmd (config.py: `os.environ.get("TESSERACT_CMD") or None`) --
    honoring TESSERACT_CMD from the environment/.env if set, falling back to
    pytesseract's PATH-based default otherwise."""
    return OCREngine(tesseract_cmd=os.environ.get("TESSERACT_CMD") or None)
