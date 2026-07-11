"""
Raw OS-level mouse move/click/drag and keyboard input, for apps with no
DOM/API path. Uses pyautogui as the OS automation backend by default, but the
controller is injected so it can be swapped or mocked in tests without a real
display/OS. See docs/PHASES.md Part 2.2.
"""
from __future__ import annotations

from typing import Protocol


class OSController(Protocol):
    def moveTo(self, x: int, y: int, duration: float = 0.0) -> None: ...
    def click(self, x: int | None = None, y: int | None = None) -> None: ...
    def doubleClick(self, x: int | None = None, y: int | None = None) -> None: ...
    def typewrite(self, text: str, interval: float = 0.0) -> None: ...
    def hotkey(self, *keys: str) -> None: ...
    def screenshot(self, region: tuple[int, int, int, int] | None = None): ...


def _default_controller() -> OSController:
    # Imported lazily so this module (and anything that imports it) doesn't
    # require a real display/OS just to be loaded — only actual desktop
    # control requires pyautogui to be importable.
    import pyautogui

    pyautogui.FAILSAFE = True  # move mouse to a screen corner to abort
    return pyautogui


class MouseKeyboard:
    def __init__(self, controller: OSController | None = None) -> None:
        self._controller = controller or _default_controller()

    def click_at(self, x: int, y: int) -> None:
        self._controller.moveTo(x, y, duration=0.1)
        self._controller.click(x, y)

    def double_click_at(self, x: int, y: int) -> None:
        self._controller.moveTo(x, y, duration=0.1)
        self._controller.doubleClick(x, y)

    def type_text(self, text: str) -> None:
        self._controller.typewrite(text, interval=0.02)

    def press_hotkey(self, *keys: str) -> None:
        self._controller.hotkey(*keys)

    def screenshot(self, path: str | None = None):
        image = self._controller.screenshot()
        if path:
            image.save(path)
        return image
