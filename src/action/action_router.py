"""
Routes a Brain-issued step to the right executor. Prefers PlaywrightDriver
for web targets (Phase 1); as of Phase 2, falls back to MouseKeyboard +
perception for desktop targets that have no DOM/API path. See docs/PHASES.md
Part 1.3, Part 2.2, and docs/CODE_LOGIC.md §17 for the routing shape this
follows.
"""
from __future__ import annotations

from src.action.mouse_keyboard import MouseKeyboard
from src.action.playwright_driver import PlaywrightDriver
from src.perception.element_detector import detect_regions, find_relevant_regions
from src.perception.ocr import OCREngine


class UnsupportedTargetType(Exception):
    pass


class ActionRouter:
    def __init__(
        self,
        playwright_driver: PlaywrightDriver,
        mouse_keyboard: MouseKeyboard | None = None,
        ocr_engine: OCREngine | None = None,
    ) -> None:
        self._playwright_driver = playwright_driver
        self._mouse_keyboard = mouse_keyboard
        self._ocr_engine = ocr_engine

    def execute(self, step: dict) -> dict:
        target_type = step.get("target_type", "web")

        if target_type == "web":
            return self._execute_web(step)
        if target_type == "desktop":
            return self._execute_desktop(step)

        raise UnsupportedTargetType(f"Unknown target_type '{target_type}'")

    def _execute_web(self, step: dict) -> dict:
        action = step["action"]
        params = step.get("params", {})

        if action == "navigate":
            self._playwright_driver.navigate(params["url"])
        elif action == "click":
            self._playwright_driver.click(params["selector"])
        elif action == "type":
            self._playwright_driver.type_text(params["selector"], params["text"])
        elif action == "scroll":
            self._playwright_driver.scroll(params.get("delta_y", 500))
        elif action == "screenshot":
            self._playwright_driver.screenshot(params.get("path", "./logs/screenshot.png"))
        else:
            raise ValueError(f"Unknown web action '{action}'")

        return {"status": "executed", "action": action, "target_type": "web"}

    def _execute_desktop(self, step: dict) -> dict:
        if self._mouse_keyboard is None:
            raise UnsupportedTargetType(
                "target_type='desktop' requires a MouseKeyboard backend — none was configured "
                "on this ActionRouter. See docs/PHASES.md Part 2.2."
            )

        action = step["action"]
        params = step.get("params", {})

        if action == "click":
            self._mouse_keyboard.click_at(*self._resolve_coords(params))
        elif action == "double_click":
            self._mouse_keyboard.double_click_at(*self._resolve_coords(params))
        elif action == "type":
            self._mouse_keyboard.type_text(params["text"])
        elif action == "hotkey":
            self._mouse_keyboard.press_hotkey(*params["keys"])
        elif action == "screenshot":
            self._mouse_keyboard.screenshot(params.get("path"))
        else:
            raise ValueError(f"Unknown desktop action '{action}'")

        return {"status": "executed", "action": action, "target_type": "desktop"}

    def _resolve_coords(self, params: dict) -> tuple[int, int]:
        """A desktop click/double_click step can specify either explicit
        (x, y), or a target_text keyword the perception layer locates on the
        current screen via OCR + element detection."""
        if "x" in params and "y" in params:
            return params["x"], params["y"]

        if "target_text" not in params:
            raise ValueError(
                "Desktop click step needs either explicit 'x'/'y' params or a 'target_text' "
                "keyword for the perception layer to locate on screen."
            )

        if self._ocr_engine is None:
            raise UnsupportedTargetType(
                "target_text-based desktop click requires an OCREngine — none was configured "
                "on this ActionRouter."
            )

        screenshot = self._mouse_keyboard.screenshot()
        words = self._ocr_engine.read(screenshot)
        regions = detect_regions(words)
        matches = find_relevant_regions(regions, [params["target_text"]])

        if not matches:
            raise ValueError(
                f"Could not locate an on-screen element matching '{params['target_text']}'"
            )

        return matches[0].center
