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

    _, kwargs = pw.chromium.launch_persistent_context.call_args
    assert kwargs["user_data_dir"] == r"C:\Users\seema\AppData\Local\Google\Chrome\User Data"
    assert kwargs["args"] == ["--profile-directory=Profile 3"]
    driver.close()


def test_launch_failure_raises_actionable_error_and_stops_playwright():
    context = MagicMock()
    pw_cm, pw = _fake_sync_playwright(context)
    pw.chromium.launch_persistent_context.side_effect = RuntimeError("lock file exists")

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        with pytest.raises(ChromeProfileLaunchError) as exc_info:
            PlaywrightDriver(profile_name="Profile 3", profiles_dir=Path("C:\\fake"))

    assert "still open" in str(exc_info.value) or "lock file exists" in str(exc_info.value)
    pw.stop.assert_called_once()


def test_profile_name_property_exposed():
    context = MagicMock()
    context.pages = []
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Profile 3", profiles_dir=Path("C:\\fake"))

    assert driver.profile_name == "Profile 3"
    driver.close()


def test_reuses_existing_page_if_present():
    existing_page = MagicMock()
    context = MagicMock()
    context.pages = [existing_page]
    pw_cm, pw = _fake_sync_playwright(context)

    with patch("src.action.playwright_driver.sync_playwright", return_value=pw_cm):
        driver = PlaywrightDriver(profile_name="Default", profiles_dir=Path("C:\\fake"))

    context.new_page.assert_not_called()
    driver.close()
