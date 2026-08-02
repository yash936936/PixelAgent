from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.action.playwright_driver import ChromeProfileLaunchError, PlaywrightDriver


def _fake_sync_playwright(context):
    pw_cm = MagicMock()
    pw = MagicMock()
    pw.chromium.launch_persistent_context.return_value = context
    pw_cm.start.return_value = pw
    return pw_cm, pw


def test_constructor_does_not_launch_chrome():
    """Real bug found live (docs/DECISIONS.md 2026-08-01): a purely
    desktop-only task crashed on a Chrome launch failure even though it
    never used a browser at all. The constructor -- and even __enter__ --
    must never launch Chrome; only a real browser action may."""
    pw_cm, pw = _fake_sync_playwright(MagicMock())

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
        with driver:
            pass  # __enter__/__exit__ with zero browser actions in between

    pw.chromium.launch_persistent_context.assert_not_called()
    pw_cm.start.assert_not_called()


def test_is_launched_false_before_any_browser_action():
    pw_cm, pw = _fake_sync_playwright(MagicMock())
    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
    assert driver.is_launched is False


def test_is_launched_true_after_a_browser_action():
    context = MagicMock()
    context.pages = []
    pw_cm, pw = _fake_sync_playwright(context)
    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
        driver.navigate("https://example.com")
    assert driver.is_launched is True
    driver.close()


def test_profile_name_property_never_launches():
    """profile_name is a plain constructor arg -- reading it must never
    trigger a launch, since it's read for gate-context display even on
    tasks that never touch the browser."""
    pw_cm, pw = _fake_sync_playwright(MagicMock())
    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Profile 3", profiles_dir=Path("C:\\fake"))
        assert driver.profile_name == "Profile 3"
    pw.chromium.launch_persistent_context.assert_not_called()


def test_close_before_any_launch_is_a_safe_noop():
    pw_cm, pw = _fake_sync_playwright(MagicMock())
    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
        driver.close()  # must not raise, even though nothing was ever launched


def test_launch_uses_profiles_dir_as_root_not_concatenated_with_profile_name():
    """Regression test for the real bug found via a live GUI run: pointing
    user_data_dir at profiles_dir/profile_name made Chromium create a fresh,
    empty 'Default' profile instead of opening the real, already-logged-in
    one. user_data_dir must be the Chrome 'User Data' root itself, with
    profile selection done via --profile-directory."""
    context = MagicMock()
    context.pages = []
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(
            profile_name="Profile 3",
            profiles_dir=Path(r"C:\Users\seema\AppData\Local\Google\Chrome\User Data"),
        )
        driver.navigate("https://example.com")  # triggers the lazy launch

    _, kwargs = pw.chromium.launch_persistent_context.call_args
    assert kwargs["user_data_dir"] == r"C:\Users\seema\AppData\Local\Google\Chrome\User Data"
    assert kwargs["args"] == ["--profile-directory=Profile 3"]
    driver.close()


def test_launch_failure_raises_actionable_error_and_stops_playwright():
    context = MagicMock()
    pw_cm, pw = _fake_sync_playwright(context)
    pw.chromium.launch_persistent_context.side_effect = RuntimeError("lock file exists")

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Profile 3", profiles_dir=Path("C:\\fake"))
        with pytest.raises(ChromeProfileLaunchError) as exc_info:
            driver.navigate("https://example.com")  # triggers the lazy launch, which fails

    assert "still open" in str(exc_info.value) or "lock file exists" in str(exc_info.value)
    pw.stop.assert_called_once()


def test_launch_only_attempted_once_even_across_multiple_calls():
    context = MagicMock()
    context.pages = []
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
        driver.navigate("https://example.com")
        driver.navigate("https://example.com/other")
        driver.current_url()

    assert pw_cm.start.call_count == 1
    assert pw.chromium.launch_persistent_context.call_count == 1
    driver.close()


def test_profile_name_property_exposed():
    context = MagicMock()
    context.pages = []
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Profile 3", profiles_dir=Path("C:\\fake"))
        driver.navigate("https://example.com")

    assert driver.profile_name == "Profile 3"
    driver.close()


def test_reuses_existing_page_if_present():
    existing_page = MagicMock()
    context = MagicMock()
    context.pages = [existing_page]
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))
        driver.navigate("https://example.com")

    context.new_page.assert_not_called()
    driver.close()
