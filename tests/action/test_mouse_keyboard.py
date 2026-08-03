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


def test_type_text_settles_after_typing(monkeypatch):
    """Real fix, docs/DECISIONS.md 2026-08-02: a live run showed 'type
    notepad' immediately followed by 'press Enter' racing ahead of
    Windows' search-results UI actually populating -- Enter fired before
    the top result was highlighted, doing nothing. Mirrors click_at's
    existing post-action settle."""
    slept_for = []
    monkeypatch.setattr("src.action.mouse_keyboard.time.sleep", lambda seconds: slept_for.append(seconds))
    mk, controller = make_mk()
    mk.type_text("notepad")
    assert slept_for == [mk._POST_TYPE_OR_HOTKEY_SETTLE_SECONDS]


def test_press_hotkey_settles_after_pressing(monkeypatch):
    slept_for = []
    monkeypatch.setattr("src.action.mouse_keyboard.time.sleep", lambda seconds: slept_for.append(seconds))
    mk, controller = make_mk()
    mk.press_hotkey("enter")
    assert slept_for == [mk._POST_TYPE_OR_HOTKEY_SETTLE_SECONDS]


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
    window before giving up."""
    mk, controller = make_mk()
    controller.get_active_window_title.side_effect = ["Command Prompt", "Untitled - Notepad"]
    mk.type_text("hello", expect_window_contains="Notepad")
    controller.activate_window.assert_called_once_with("Notepad")
    controller.typewrite.assert_called_once_with("hello", interval=0.02)


def test_type_text_does_not_retry_activation_faster_than_the_retry_interval():
    """Within a short timeout (well under _ACTIVATION_RETRY_INTERVAL_SECONDS),
    activation should only be attempted once -- spamming it on every 0.2s
    poll would be wasteful and could itself cause focus-stealing flicker."""
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Command Prompt"  # never matches
    with pytest.raises(RuntimeError):
        mk.type_text("hello", expect_window_contains="Notepad", timeout=0.05)
    controller.activate_window.assert_called_once_with("Notepad")


def test_type_text_retries_activation_periodically_for_a_slow_launching_app():
    """Real fix, docs/DECISIONS.md 2026-08-02: a live run showed a single,
    early activation attempt fail because a cold-launching app (Notepad)
    hadn't created its window yet -- the fix must retry activation more
    than once for a genuinely slow-to-appear window, not give up after one
    early miss."""
    mk, controller = make_mk()
    controller.get_active_window_title.return_value = "Command Prompt"  # never matches
    # Fake the passage of real time across multiple retry-interval windows
    # without an actual multi-second test: monotonic() advances by a large
    # fixed step each call, well past _ACTIVATION_RETRY_INTERVAL_SECONDS.
    fake_clock = {"t": 0.0}

    def fake_monotonic():
        fake_clock["t"] += 1.0
        return fake_clock["t"]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.action.mouse_keyboard.time.monotonic", fake_monotonic)
        with pytest.raises(RuntimeError):
            mk.type_text("hello", expect_window_contains="Notepad", timeout=10.0)

    assert controller.activate_window.call_count >= 2


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
