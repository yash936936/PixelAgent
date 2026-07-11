"""
Routes a Brain-issued step to the right executor. In Phase 1 it only ever
routes to PlaywrightDriver; the branch for pixel-level desktop control
(mouse_keyboard.py) is added in Phase 2 — see docs/PHASES.md Part 2.2 and
docs/CODE_LOGIC.md §17 for the eventual desktop-control branch shape.
"""
from __future__ import annotations

from src.action.playwright_driver import PlaywrightDriver


class UnsupportedTargetType(Exception):
    pass


class ActionRouter:
    def __init__(self, playwright_driver: PlaywrightDriver) -> None:
        self._playwright_driver = playwright_driver

    def execute(self, step: dict) -> dict:
        target_type = step.get("target_type", "web")

        if target_type == "web":
            return self._execute_web(step)

        # Phase 1 has no desktop-control backend yet.
        raise UnsupportedTargetType(
            f"target_type='{target_type}' is not supported until Phase 2 "
            "(src/action/mouse_keyboard.py). See docs/PHASES.md Part 2.2."
        )

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
