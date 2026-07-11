"""
Wraps Playwright: launch with a named Chrome profile, navigate, click by
selector/text, type, screenshot. The only Action file in Phase 1 —
mouse_keyboard.py (raw OS-level control) is added in Phase 2.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


class PlaywrightDriver:
    def __init__(self, profile_name: str, profiles_dir: Path, headless: bool = False) -> None:
        self._profile_name = profile_name
        self._pw = sync_playwright().start()
        user_data_dir = str(profiles_dir / profile_name)
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
        )
        self._page: Page = (
            self._context.pages[0] if self._context.pages else self._context.new_page()
        )

    def navigate(self, url: str) -> None:
        self._page.goto(url, wait_until="domcontentloaded")

    def click(self, selector: str) -> None:
        self._page.click(selector, timeout=10_000)

    def type_text(self, selector: str, text: str) -> None:
        self._page.fill(selector, text, timeout=10_000)

    def scroll(self, delta_y: int = 500) -> None:
        self._page.mouse.wheel(0, delta_y)

    def screenshot(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=path)

    def current_url(self) -> str:
        return self._page.url

    def current_title(self) -> str:
        return self._page.title()

    def close(self) -> None:
        self._context.close()
        self._pw.stop()

    def __enter__(self) -> "PlaywrightDriver":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
