from unittest.mock import MagicMock

from src.action.mouse_keyboard import MouseKeyboard


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
