"""
Wraps Playwright: launch against a real Chrome "User Data" root and select
an existing, already-logged-in profile within it, navigate, click by
selector/text, type, screenshot. The only Action file in Phase 1 —
mouse_keyboard.py (raw OS-level control) is added in Phase 2.

IMPORTANT — profile selection: `profiles_dir` (PROFILES_DIR in .env) must be
the actual Chrome "User Data" root, e.g.
C:\\Users\\<you>\\AppData\\Local\\Google\\Chrome\\User Data — NOT a
profile-specific subfolder. `profile_name` (DEFAULT_CHROME_PROFILE) is the
real on-disk profile folder name (e.g. "Profile 3"), which you find via
chrome://version -> "Profile Path" while that profile is active, NOT the
friendly display name shown in Chrome's "Who's using Chrome?" picker.
launch_persistent_context's `user_data_dir` is Chromium's whole profile
*root*, so profile selection has to happen via the `--profile-directory`
launch arg, not by pointing user_data_dir directly at a profile subfolder —
doing that (an earlier bug in this file) makes Chromium create a brand-new,
empty "Default" profile inside that subfolder instead of opening the real,
already-logged-in one, which is why a task could land on a logged-out
marketing page instead of an authenticated inbox. See docs/DECISIONS.md.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright


class ChromeProfileLaunchError(Exception):
    """Raised when Chromium fails to launch against the requested profile —
    most commonly because the real Chrome is still open on that same
    profile (its lock file blocks a second instance)."""


class PlaywrightDriver:
    def __init__(self, profile_name: str, profiles_dir: Path, headless: bool = False) -> None:
        self._profile_name = profile_name
        self._pw = sync_playwright().start()
        user_data_dir = str(profiles_dir)

        try:
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                args=[f"--profile-directory={profile_name}"],
            )
        except Exception as exc:  # noqa: BLE001 — re-raised with an actionable message
            self._pw.stop()
            raise ChromeProfileLaunchError(
                f"Could not launch Chrome against profile '{profile_name}' in "
                f"'{user_data_dir}'. The most common cause: your real Chrome is still "
                f"open using this same profile — its lock file blocks a second instance "
                f"from using it. Fully close Chrome (check the system tray/task manager, "
                f"not just the window) and try again. Original error: {exc}"
            ) from exc

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

    @property
    def profile_name(self) -> str:
        """Fix for a gap flagged in review: gate.py/prompt_ui.py always
        claimed to show the target account/profile, but nothing exposed it
        anywhere -- this is what main.py/orchestrator.py now read to build
        that GateContext field."""
        return self._profile_name

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
