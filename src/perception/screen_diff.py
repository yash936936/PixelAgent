"""
Compares before/after screenshots to verify a step had the expected effect.
Feeds src/brain/replanner.py when a mismatch is detected. See docs/PHASES.md
Part 2.1 and Part 2.3.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops


@dataclass
class DiffResult:
    changed: bool
    change_ratio: float  # 0.0 (identical) to 1.0 (completely different)


def compare(
    before: Image.Image | str | Path, after: Image.Image | str | Path, threshold: float = 0.01
) -> DiffResult:
    if isinstance(before, (str, Path)):
        before = Image.open(before)
    if isinstance(after, (str, Path)):
        after = Image.open(after)

    if before.size != after.size:
        return DiffResult(changed=True, change_ratio=1.0)

    diff = ImageChops.difference(before.convert("RGB"), after.convert("RGB"))
    if diff.getbbox() is None:
        return DiffResult(changed=False, change_ratio=0.0)

    histogram = diff.histogram()
    total_values = before.size[0] * before.size[1] * 3
    # histogram has 256 buckets per channel (R,G,B); bucket 0 across each
    # channel means "no difference at that pixel/channel" — everything else
    # is some amount of change.
    nonzero_buckets = sum(histogram[1:256]) + sum(histogram[257:512]) + sum(histogram[513:768])
    change_ratio = min(1.0, nonzero_buckets / total_values) if total_values else 0.0

    return DiffResult(changed=change_ratio > threshold, change_ratio=change_ratio)


def matches_expected(
    before: Image.Image | str | Path,
    after: Image.Image | str | Path,
    expect_change: bool,
    threshold: float = 0.01,
) -> bool:
    """expect_change: True if the step should have visibly changed the screen
    (navigation, a click that opens/closes something, typed text appearing).
    False for steps that should leave the screen visually unchanged."""
    result = compare(before, after, threshold=threshold)
    return result.changed == expect_change
