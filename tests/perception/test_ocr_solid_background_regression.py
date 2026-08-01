"""
Regression test for the OCR gap discovered by the real-pixel integration
harness (tests/integration/test_real_ocr_pipeline.py): Tesseract's
`textord` layout analysis was discarding solid-color rectangular regions
(e.g. a standard filled button) as non-text "picture" blocks before OCR
ever ran on them -- regardless of the text color/contrast inside them.

This uses a real Tesseract call (not a mock) against a real, small,
synthetically-drawn image, so it stays fast and fully offline (no
Playwright/Chromium needed, unlike the fuller integration tier) while
still exercising the actual bug rather than a hand-built OCRWord list
that could never have caught it in the first place.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from src.perception.ocr import OCREngine


def _solid_button_image(text: str = "Submit") -> Image.Image:
    """A minimal repro of the real failure: a large solid-color filled
    rectangle with light text on it, on an otherwise blank canvas -- this
    is what a typical rendered primary button looks like as pixels."""
    img = Image.new("RGB", (300, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 260, 110), fill=(45, 108, 223))  # solid blue button
    draw.text((70, 62), text, fill="white")
    return img


def test_ocr_finds_text_inside_a_solid_color_button():
    words = OCREngine().read(_solid_button_image())
    texts = [w.text for w in words]
    assert any("Submit" in t or "submit" in t.lower() for t in texts), (
        f"OCREngine failed to read text inside a solid-color button block, got: {texts} -- "
        "this is the textord_min_linesize regression, see ocr.py's module docstring"
    )


def test_ocr_still_finds_plain_text_on_white_background():
    """Guard against the fix regressing the common, already-working case."""
    img = Image.new("RGB", (300, 60), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Username", fill="black")

    words = OCREngine().read(img)
    texts = [w.text for w in words]
    assert any("Username" in t for t in texts)
