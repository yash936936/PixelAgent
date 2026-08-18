"""
Diagnostic script for the real_ocr_finds_submit_button_text failure on Tesseract
5.5.0.20241111 (2026-08-17, docs/DECISIONS.md). Run this ON THE MACHINE where the
real test is failing -- this can't be reproduced in the sandboxed dev environment
this fix would otherwise be written in (no real Chromium binary available there,
and only Tesseract 5.3.4, which does NOT reproduce this failure).

Usage (from the repo root, with your venv active):
    python diagnose_ocr_failure.py

Prints, for each candidate Tesseract config, whether it finds "Submit" on the
real button.html fixture rendered by your real installed Chromium. Paste the
full output back -- whichever config(s) actually work becomes the real fix for
src/perception/ocr.py's _TESSERACT_CONFIG, verified against your real
environment rather than guessed.
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pytesseract
from dotenv import load_dotenv
from PIL import Image
from playwright.sync_api import sync_playwright

load_dotenv()

FIXTURE_PATH = Path(__file__).parent / "tests" / "integration" / "fixtures" / "pages" / "button.html"

CANDIDATE_CONFIGS = {
    "current (textord_min_linesize only)": "-c textord_min_linesize=1.0",
    "psm 11 (sparse text) alone": "--psm 11",
    "psm 11 + textord_min_linesize": "--psm 11 -c textord_min_linesize=1.0",
    "psm 6 (single uniform block) + textord_min_linesize": "--psm 6 -c textord_min_linesize=1.0",
    "psm 12 (sparse text + OSD) + textord_min_linesize": "--psm 12 -c textord_min_linesize=1.0",
    "textord_min_linesize + tabfind_find_tables off": "-c textord_min_linesize=1.0 -c textord_tabfind_find_tables=0",
    "psm 11 + tabfind_find_tables off": "--psm 11 -c textord_tabfind_find_tables=0",
    "no special config at all (baseline)": "",
}


def main() -> None:
    tesseract_cmd = os.environ.get("TESSERACT_CMD") or None
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    print(f"Tesseract version: {pytesseract.get_tesseract_version()}")
    print(f"Fixture: {FIXTURE_PATH}")
    if not FIXTURE_PATH.exists():
        print("ERROR: fixture file not found -- run this from the repo root.")
        raise SystemExit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(FIXTURE_PATH.resolve().as_uri())
        screenshot_bytes = page.screenshot()
        browser.close()

    image = Image.open(io.BytesIO(screenshot_bytes))
    image.save("diagnose_ocr_screenshot.png")
    print("Saved the real screenshot to diagnose_ocr_screenshot.png for visual inspection.\n")

    print(f"{'Config':<60} {'Words found'}")
    print("-" * 100)
    for label, config in CANDIDATE_CONFIGS.items():
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config)
            texts = [t.strip() for t in data["text"] if t.strip()]
        except Exception as exc:  # noqa: BLE001 - diagnostic script, report and continue
            texts = [f"ERROR: {exc}"]
        found_submit = any("submit" in t.lower() for t in texts)
        marker = "FOUND SUBMIT" if found_submit else "missing"
        print(f"{label:<60} [{marker}] {texts}")


if __name__ == "__main__":
    main()
