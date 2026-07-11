"""
Converts raw OCR output into structured ScreenRegion elements the Brain can
target ("the Submit button") instead of raw pixel coordinates, and retrieves
only the regions relevant to the current sub-goal instead of handing the
Brain everything detected on screen — the PixelRAG-style retrieval pattern
from docs/CODE_LOGIC.md §3. See docs/PHASES.md Part 2.1.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.perception.ocr import OCRWord

_BUTTON_KEYWORDS = {
    "submit", "ok", "cancel", "save", "next", "continue", "login", "log in",
    "sign in", "sign up", "search", "star", "send", "close", "open", "confirm",
    "approve", "deny", "yes", "no", "back",
}


@dataclass
class ScreenRegion:
    text: str
    bbox: tuple[int, int, int, int]
    kind: str  # "button" | "field" | "link" | "text"
    center: tuple[int, int]


def _classify(text: str) -> str:
    lowered = text.lower().strip()
    if lowered in _BUTTON_KEYWORDS:
        return "button"
    if lowered.endswith(":") or lowered.endswith("?"):
        return "field"
    return "text"


def detect_regions(words: list[OCRWord]) -> list[ScreenRegion]:
    """Converts raw OCR words into classified, centered regions. Word-level
    for now — line/paragraph grouping is a candidate future refinement, not
    required for Phase 2's success criterion."""
    regions: list[ScreenRegion] = []
    for w in words:
        left, top, width, height = w.bbox
        center = (left + width // 2, top + height // 2)
        regions.append(ScreenRegion(text=w.text, bbox=w.bbox, kind=_classify(w.text), center=center))
    return regions


def find_relevant_regions(regions: list[ScreenRegion], goal_keywords: list[str]) -> list[ScreenRegion]:
    """Retrieve only the regions relevant to the current sub-goal instead of
    handing the Brain every detected element on screen."""
    goal_keywords_lower = [k.lower() for k in goal_keywords if k.strip()]
    if not goal_keywords_lower:
        return []
    return [r for r in regions if any(k in r.text.lower() for k in goal_keywords_lower)]
