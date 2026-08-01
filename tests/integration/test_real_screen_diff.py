"""
Real-pixel screen_diff validation. tests/perception/test_screen_diff.py
only proves compare()'s math is correct on hand-built solid-color images;
it says nothing about whether the default threshold=0.01 is well-calibrated
against real rendering artifacts (anti-aliasing, sub-pixel font hinting,
CSS animation) that a real screenshot has and a synthetic solid-color
image never does. That calibration question is exactly what's flagged in
docs/STATUS.md's "zero live validation" gap -- this is the offline,
deterministic proxy for it.
"""
from __future__ import annotations

import io

from PIL import Image

from src.perception import screen_diff

from .conftest import fixture_url


def _screenshot_to_image(page) -> Image.Image:
    return Image.open(io.BytesIO(page.screenshot())).convert("RGB")


def test_real_click_that_changes_the_page_is_detected(page):
    """True-positive case: clicking 'Open Panel' visibly changes a large
    colored region. This must register as changed."""
    page.goto(fixture_url("dynamic_change.html"))
    before = _screenshot_to_image(page)

    page.click("#toggle-btn")
    page.wait_for_timeout(100)  # let the class-toggle repaint settle
    after = _screenshot_to_image(page)

    result = screen_diff.compare(before, after)
    assert result.changed is True
    assert result.change_ratio > 0.01
    assert screen_diff.matches_expected(before, after, expect_change=True)


def test_real_identical_screenshots_of_static_page_are_unchanged(page):
    """Two screenshots of the exact same static render, no interaction in
    between, must register as unchanged -- the real-pixel equivalent of
    test_screen_diff.py's identical-image case, but through an actual
    render pass twice instead of one PIL object compared to itself."""
    page.goto(fixture_url("button.html"))
    first = _screenshot_to_image(page)
    second = _screenshot_to_image(page)

    result = screen_diff.compare(first, second)
    assert result.changed is False
    assert result.change_ratio == 0.0


def test_real_blinking_cursor_animation_false_positive_risk(page):
    """Characterizes, rather than blindly asserts, the real false-positive
    risk flagged in review: a page with only a small blinking-cursor-style
    CSS animation and otherwise static content. Two screenshots taken far
    enough apart to plausibly land on opposite phases of the blink.

    This does not assert `changed is False` unconditionally -- a real
    animated element legitimately does change some pixels, and asserting
    the tool must ignore it would hide a real calibration question rather
    than answer it. Instead this asserts the change stays SMALL (a tiny
    blinking caret must not be scored anywhere near the same magnitude as
    the large-panel change in the true-positive test above), and prints
    the actual ratio so a human reviewer can decide if the default 0.01
    threshold needs adjusting for this kind of content.
    """
    page.goto(fixture_url("blinking_cursor.html"))
    before = _screenshot_to_image(page)
    # Half the CSS animation's 1s period, to try to land on the opposite
    # visibility phase of the blink.
    page.wait_for_timeout(500)
    after = _screenshot_to_image(page)

    result = screen_diff.compare(before, after)
    print(
        f"\n[blinking cursor] change_ratio={result.change_ratio:.5f} "
        f"changed={result.changed} (default threshold=0.01)"
    )
    # A ~2px-wide cursor toggling on an 800x600 canvas is a tiny fraction
    # of the frame -- nowhere near the >0.5 true-positive case above. If
    # this ever creeps close to 0.01, that's a real signal the threshold
    # needs a second look for text-input-heavy screens, not a flaky test.
    assert result.change_ratio < 0.01, (
        f"a single blinking cursor changed {result.change_ratio:.5f} of the "
        "frame -- more than expected for a ~2px element; re-examine the "
        "default threshold before trusting it on real text-entry screens"
    )
