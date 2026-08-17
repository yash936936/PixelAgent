"""
Runs the actual perception pipeline (OCREngine -> detect_regions ->
find_relevant_regions) against a real screenshot of a real rendered page,
using the real Tesseract binary -- not a hand-built OCRWord list. This is
what tests/perception/test_element_detector.py cannot tell you: whether
Tesseract's real bounding boxes on real rendered text are close enough to
element_detector's classification rules to actually find the right click
target.
"""
from __future__ import annotations

import io

from PIL import Image

from src.perception.element_detector import detect_regions, find_relevant_regions

from .conftest import fixture_url
from tests._ocr_test_support import real_ocr_engine


def _screenshot_to_image(page) -> Image.Image:
    png_bytes = page.screenshot()
    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def test_real_ocr_finds_submit_button_text(page):
    page.goto(fixture_url("button.html"))
    image = _screenshot_to_image(page)

    words = real_ocr_engine().read(image)
    texts = [w.text for w in words]

    assert "Submit" in texts, f"Tesseract did not find 'Submit' among: {texts}"


def test_real_ocr_pipeline_locates_clickable_submit_region(page):
    """End-to-end: real screenshot -> real OCR -> region classification ->
    keyword filtering -> a center point that actually falls within the
    button's real rendered bounding box (cross-checked against Playwright's
    own element geometry, which we trust as ground truth here)."""
    page.goto(fixture_url("button.html"))
    image = _screenshot_to_image(page)

    words = real_ocr_engine().read(image)
    regions = detect_regions(words)
    matches = find_relevant_regions(regions, ["submit"])

    assert len(matches) == 1, f"expected exactly one 'submit' match, got: {matches}"
    match = matches[0]

    # Ground truth: where Playwright itself says the button actually is.
    handle = page.query_selector("#submit-btn")
    box = handle.bounding_box()
    assert box is not None

    center_x, center_y = match.center
    assert box["x"] <= center_x <= box["x"] + box["width"], (
        f"OCR-derived center x={center_x} falls outside real button x-range "
        f"[{box['x']}, {box['x'] + box['width']}]"
    )
    assert box["y"] <= center_y <= box["y"] + box["height"], (
        f"OCR-derived center y={center_y} falls outside real button y-range "
        f"[{box['y']}, {box['y'] + box['height']}]"
    )


def test_real_ocr_pipeline_username_field_classified_as_field(page):
    page.goto(fixture_url("button.html"))
    image = _screenshot_to_image(page)

    words = real_ocr_engine().read(image)
    regions = detect_regions(words)
    field_regions = [r for r in regions if r.kind == "field"]

    assert any("Username" in r.text for r in field_regions), (
        f"expected a 'field'-classified region containing 'Username', got: {regions}"
    )
