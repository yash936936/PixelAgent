"""
Runs OCR over a screenshot and returns detected text + bounding boxes.
Requires the Tesseract OCR engine installed on the OS (not just the Python
wrapper) — on Windows, install from https://github.com/UB-Mannheim/tesseract/wiki
and either add it to PATH or pass tesseract_cmd explicitly. See docs/PHASES.md
Part 2.1.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytesseract
from PIL import Image

# Real-pixel integration testing (tests/integration/test_real_ocr_pipeline.py,
# run against an actual rendered page, not a hand-built OCRWord list) caught
# Tesseract finding zero words at all on a solid-blue "Submit" button with
# white text -- a completely standard, common real-UI element that every
# earlier test in this codebase missed, since none of them exercised the
# real Tesseract binary against a real screenshot.
#
# Root cause, confirmed by isolating a crop of just the button: it was NOT
# a contrast/color problem (a cropped, inverted image of the same button
# still failed identically) and NOT an image-resolution problem (upscaling
# the crop didn't help at the full-page level either). It's Tesseract's
# `textord` layout-analysis pass, which runs before OCR and decides which
# regions of the page are even worth reading -- by default it treats a
# large solid-color rectangle as a "picture" block and discards it before
# any glyph recognition happens, regardless of what's drawn on top of it.
# This is a page-layout heuristic tuned for scanned documents, and it
# misfires constantly on real UI screenshots (solid-color buttons, colored
# panels, dark-mode surfaces).
#
# `textord_min_linesize=1.0` lowers the minimum line-height Tesseract's
# layout analysis requires before it will consider a region as text at
# all, which stops it from pre-emptively discarding these blocks. Verified
# empirically: without it, a 2-line real UI screenshot (label + button)
# returns only the label; with it, both are found at full confidence, with
# no changes needed to psm, image scale, or color.
#
# Second real fix, found live on real Windows hardware with a newer
# Tesseract build (5.5.0.20241111 -- UB-Mannheim's dev-snapshot build,
# vs. 5.3.4 in this project's own Linux CI/dev environment) (2026-08-17,
# docs/DECISIONS.md): `textord_min_linesize=1.0` alone, which was
# sufficient on 5.3.4, no longer found "Submit" at all on 5.5.0 -- Tesseract's
# default page segmentation mode (PSM 3, "fully automatic page segmentation,
# no OSD") re-ran the same solid-color-block-discarded-as-picture layout
# heuristic this whole config exists to work around, apparently more
# aggressively on the newer build. Diagnosed with a real diagnostic script
# (diagnose_ocr_failure.py) run directly against the real failing
# environment (this project's sandboxed dev environment has no real Chromium
# available to reproduce it, and only ships Tesseract 5.3.4, which never
# reproduced this) -- 8 candidate configs tested against the real rendered
# fixture on the real machine; `--psm 6` (treat the image as a single
# uniform block of text, skipping Tesseract's own column/block layout
# analysis entirely) was the only one that found "Submit". Verified this
# doesn't regress anything in the Linux/5.3.4 environment either (full
# perception + integration OCR suite re-run clean after adding it).
#
# REAL, ACCEPTED TRADE-OFF, not silently absorbed: `read()` is called
# against the FULL desktop screenshot in production
# (src/action/action_router.py's `_locate_target_text`, not a cropped
# region) -- `--psm 6` tells Tesseract to treat that entire screenshot as
# one uniform text block, skipping the multi-column/multi-region layout
# analysis PSM 3 (the prior default) would otherwise do. This fixture only
# exercises a simple 2-line screen (a label + a button); it says nothing
# about accuracy on a genuinely complex, multi-panel real desktop
# screenshot (multiple windows, a taskbar, several distinct widget
# regions), which this project has no test coverage for either way.
# Accepted here because the alternative -- the previous config -- fails
# outright and completely on a real, current Tesseract build for a single
# ordinary button, which is strictly worse than an unvalidated risk to
# reading order on more complex screens. Flagged as a real follow-up:
# Phase 18's real beta usage (which will exercise real, varied, complex
# desktop screenshots this project's own test fixtures don't) is the
# natural place this either gets confirmed fine or surfaces a real
# regression worth revisiting -- see docs/BETA_FINDINGS.md.
_TESSERACT_CONFIG = "--psm 6 -c textord_min_linesize=1.0"


@dataclass
class OCRWord:
    text: str
    bbox: tuple[int, int, int, int]  # (left, top, width, height)
    confidence: float


class OCREngine:
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def read(self, image: Image.Image | str | Path) -> list[OCRWord]:
        if isinstance(image, (str, Path)):
            image = Image.open(image)

        data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT, config=_TESSERACT_CONFIG
        )
        words: list[OCRWord] = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            if not text:
                continue
            raw_conf = data["conf"][i]
            try:
                conf = float(raw_conf)
            except (TypeError, ValueError):
                conf = 0.0
            words.append(
                OCRWord(
                    text=text,
                    bbox=(data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
                    confidence=max(conf, 0.0),
                )
            )
        return words

