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

        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
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
