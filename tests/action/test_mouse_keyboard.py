from unittest.mock import MagicMock

import pytest

from src.action.mouse_keyboard import MouseKeyboard


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch):
    """Every test in this file should run instantly -- the real settle/poll
    delays (click_at's 0.3s settle, type_text's polling loop) are for real
    hardware timing, not something unit tests should actually wait through."""
    monkeypatch.setattr("src.action.mouse_keyboard.time.sleep", lambda *_: None)


def make_mk():
    controller = MagicMock()
    return MouseKeyboard(controller=controller), controller


def test_click_at_moves_then_clicks():
    mk, controller = make_mk()
    mk.click_at(100, 200)
    controller.moveTo.assert_called_once_with(100, 200, duration=0.1)
    controller.click.assert_called_once_with(100, 200)


def test_double_click_at():
    mk, controller = make_mk()
    mk.double_click_at(50, 60)
    controller.moveTo.assert_called_once_with(50, 60, duration=0.1)
    controller.doubleClick.assert_called_once_with(50, 60)


def test_type_text():
    mk, controller = make_mk()
    mk.type_text("hello")
    controller.typewrite.assert_called_once_with("hello", interval=0.02)


def test_type_text_with_no_expected_window_types_immediately_unverified():
    """Backward-compatible default: omitting expect_window_contains skips
    verification entirely, same as the old behavior."""
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Completely Unrelated Window"
    mk.type_text("hello")
    controller.typewrite.assert_called_once_with("hello", interval=0.02)


def test_type_text_waits_for_expected_window_then_types():
    """Real bug fix, docs/DECISIONS.md 2026-08-01: type_text must verify
    the target window actually has focus before typing, not type blindly."""
    mk, controller = make_mk()
    # First poll: wrong window still focused (Notepad still launching).
    # Second poll: Notepad has gained focus.
    controller.get_active_window_title.side_effect = ["Command Prompt", "Untitled - Notepad"]
    mk.type_text("This is a test message.", expect_window_contains="Notepad")
    controller.typewrite.assert_called_once_with("This is a test message.", interval=0.02)


def test_type_text_matches_case_insensitively():
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "untitled - notepad"
    mk.type_text("hello", expect_window_contains="Notepad")
    controller.typewrite.assert_called_once_with("hello", interval=0.02)


def test_type_text_raises_instead_of_typing_into_wrong_window():
    """This is exactly the live-run failure mode: the expected window never
    gains focus in time. Must raise, and critically must NEVER call
    typewrite() in this case -- the whole point of the fix is that typing
    into the wrong window (e.g. a terminal) is worse than failing loudly."""
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Command Prompt"  # never changes

    with pytest.raises(RuntimeError, match="Notepad"):
        mk.type_text("This is a test message.", expect_window_contains="Notepad", timeout=0.01)

    controller.typewrite.assert_not_called()


def test_type_text_attempts_to_activate_expected_window_on_mismatch():
    """Real fix, docs/DECISIONS.md 2026-08-01: 'the target app goes to the
    background and the next action fails' -- rather than only passively
    waiting, type_text must actively try to reclaim focus for the expected
    window once before giving up."""
    mk, controller = make_mk()
    controller.get_active_window_title.side_effect = ["Command Prompt", "Untitled - Notepad"]
    mk.type_text("hello", expect_window_contains="Notepad")
    controller.activate_window.assert_called_once_with("Notepad")
    controller.typewrite.assert_called_once_with("hello", interval=0.02)


def test_type_text_only_attempts_activation_once_not_every_poll():
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Command Prompt"  # never matches
    with pytest.raises(RuntimeError):
        mk.type_text("hello", expect_window_contains="Notepad", timeout=0.05)
    controller.activate_window.assert_called_once_with("Notepad")


def test_type_text_no_activation_attempt_when_already_focused():
    """If the expected window already has focus on the very first check,
    there's nothing to activate -- must not call activate_window at all."""
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Untitled - Notepad"
    mk.type_text("hello", expect_window_contains="Notepad")
    controller.activate_window.assert_not_called()


def test_press_hotkey():
    mk, controller = make_mk()
    mk.press_hotkey("ctrl", "c")
    controller.hotkey.assert_called_once_with("ctrl", "c")


def test_screenshot_saves_when_path_given():
    mk, controller = make_mk()
    fake_image = MagicMock()
    controller.screenshot.return_value = fake_image

    result = mk.screenshot(path="./out.png")

    fake_image.save.assert_called_once_with("./out.png")
    assert result is fake_image


def test_screenshot_no_save_when_no_path():
    mk, controller = make_mk()
    fake_image = MagicMock()
    controller.screenshot.return_value = fake_image

    result = mk.screenshot()

    fake_image.save.assert_not_called()
    assert result is fake_image
