"""
Raw OS-level mouse move/click/drag and keyboard input, for apps with no
DOM/API path. Uses pyautogui as the OS automation backend by default, but the
controller is injected so it can be swapped or mocked in tests without a real
display/OS. See docs/PHASES.md Part 2.2.

Fix for a real, serious bug found on Phase 7's first fully-completed
live desktop task (docs/DECISIONS.md 2026-08-01): type_text() previously
called pyautogui.typewrite() completely blindly, with no verification that
the intended target window actually had OS keyboard focus, and no wait
after a click for a newly-launched app (e.g. Notepad) to actually finish
opening. In the live trace, the click-then-type sequence outran Notepad's
actual launch time, and the test message was typed into whatever window
still had focus (the terminal that launched Pixel) instead -- the task
still reported "done" and every step reported "executed", because nothing
anywhere checked that typing actually landed where it was supposed to.
This is now checked, not assumed: type_text() accepts an optional
`expect_window_contains` keyword and polls the real active window title
before typing, raising a loud, actionable error instead of silently typing
into the wrong window if the expected window never gains focus in time.
"""
from __future__ import annotations

import time
from typing import Protocol


class OSController(Protocol):
    def moveTo(self, x: int, y: int, duration: float = 0.0) -> None: ...
    def click(self, x: int | None = None, y: int | None = None) -> None: ...
    def doubleClick(self, x: int | None = None, y: int | None = None) -> None: ...
    def typewrite(self, text: str, interval: float = 0.0) -> None: ...
    def hotkey(self, *keys: str) -> None: ...
    def screenshot(self, region: tuple[int, int, int, int] | None = None): ...
    def get_active_window_title(self) -> str | None: ...
    def activate_window(self, title_keyword: str) -> bool: ...


def _default_controller() -> OSController:
    # Imported lazily so this module (and anything that imports it) doesn't
    # require a real display/OS just to be loaded — only actual desktop
    # control requires pyautogui to be importable.
    import pyautogui

    pyautogui.FAILSAFE = True  # move mouse to a screen corner to abort

    class _PyAutoGuiController:
        """Thin wrapper adding get_active_window_title() -- pyautogui itself
        doesn't expose this as a top-level function; it delegates to
        pygetwindow's getActiveWindow() on Windows/macOS. Wrapped in a
        try/except since this is a best-effort check: if it's ever
        unavailable on some platform/config, type_text() should fail
        loudly (see below) rather than silently skip the check, but the
        controller itself shouldn't crash just from being constructed."""

        def __getattr__(self, name):
            return getattr(pyautogui, name)

        def get_active_window_title(self) -> str | None:
            try:
                window = pyautogui.getActiveWindow()
                return window.title if window is not None else None
            except Exception:  # noqa: BLE001 - genuinely best-effort
                return None

        def activate_window(self, title_keyword: str) -> bool:
            """Best-effort attempt to bring a window matching
            title_keyword to the foreground -- this is the actual fix for
            "the target app goes to the background and the next action
            fails" (docs/DECISIONS.md 2026-08-01): rather than just
            detecting the wrong window has focus and giving up, actively
            try to reclaim focus for the intended one first. Returns
            whether a matching window was found at all (not whether
            activation definitely succeeded -- Windows can still refuse a
            focus-steal request from a background process in some cases,
            which is exactly why type_text() re-checks focus afterward
            rather than trusting this call blindly)."""
            try:
                windows = pyautogui.getWindowsWithTitle(title_keyword)
                if not windows:
                    return False
                windows[0].activate()
                return True
            except Exception:  # noqa: BLE001 - genuinely best-effort
                return False

    return _PyAutoGuiController()


class MouseKeyboard:
    #: How long to wait, polling, for an expected window to gain focus
    #: before giving up and raising -- see type_text()'s
    #: expect_window_contains parameter.
    DEFAULT_FOCUS_TIMEOUT_SECONDS = 5.0
    _FOCUS_POLL_INTERVAL_SECONDS = 0.2

    #: Brief pause after a click, before anything else happens -- gives a
    #: newly-launched app a moment to at least start appearing before the
    #: next step queries screen state. This is NOT a substitute for the
    #: real fix (checking actual window focus in type_text()) -- it's a
    #: cheap, harmless floor underneath it, since some UI transitions have
    #: no distinct "window title" to poll for (e.g. a menu opening).
    _POST_CLICK_SETTLE_SECONDS = 0.3

    def __init__(self, controller: OSController | None = None) -> None:
        self._controller = controller or _default_controller()

    def click_at(self, x: int, y: int) -> None:
        self._controller.moveTo(x, y, duration=0.1)
        self._controller.click(x, y)
        time.sleep(self._POST_CLICK_SETTLE_SECONDS)

    def double_click_at(self, x: int, y: int) -> None:
        self._controller.moveTo(x, y, duration=0.1)
        self._controller.doubleClick(x, y)
        time.sleep(self._POST_CLICK_SETTLE_SECONDS)

    def type_text(
        self,
        text: str,
        expect_window_contains: str | None = None,
        timeout: float = DEFAULT_FOCUS_TIMEOUT_SECONDS,
    ) -> None:
        """Types at the current OS keyboard focus.

        If `expect_window_contains` is given, polls the real active window
        title (case-insensitively) until it contains that substring, up to
        `timeout` seconds, before typing a single character -- this is the
        actual fix for the live-run bug above. If the expected window never
        gains focus in time, raises RuntimeError rather than typing into
        whatever window happens to have focus. If `expect_window_contains`
        is omitted (the default, preserving old behavior for callers that
        don't have an expected window to check), types immediately with no
        verification -- callers that care about correctness should always
        pass it when the target window is knowable."""
        if expect_window_contains:
            deadline = time.monotonic() + timeout
            last_seen_title: str | None = None
            attempted_activation = False
            while time.monotonic() < deadline:
                last_seen_title = self._controller.get_active_window_title()
                if last_seen_title and expect_window_contains.lower() in last_seen_title.lower():
                    break
                if not attempted_activation:
                    # Real fix (docs/DECISIONS.md 2026-08-01) for "the target
                    # app goes to the background and the next action fails":
                    # actively try to reclaim focus once, instead of only
                    # ever passively waiting and hoping it regains focus on
                    # its own (e.g. after the confirmation-gate prompt
                    # itself stole focus to the terminal).
                    self._controller.activate_window(expect_window_contains)
                    attempted_activation = True
                time.sleep(self._FOCUS_POLL_INTERVAL_SECONDS)
            else:
                raise RuntimeError(
                    f"Expected a window containing {expect_window_contains!r} to gain focus "
                    f"within {timeout}s before typing, but the active window was "
                    f"{last_seen_title!r}. Refusing to type into the wrong window -- this is "
                    "exactly the bug found in the 2026-08-01 live run where a test message was "
                    "typed into the terminal instead of Notepad."
                )

        self._controller.typewrite(text, interval=0.02)

    def press_hotkey(self, *keys: str) -> None:
        self._controller.hotkey(*keys)

    def screenshot(self, path: str | None = None):
        image = self._controller.screenshot()
        if path:
            image.save(path)
        return image
