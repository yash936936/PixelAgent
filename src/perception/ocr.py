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
_TESSERACT_CONFIG = "-c textord_min_linesize=1.0"


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

