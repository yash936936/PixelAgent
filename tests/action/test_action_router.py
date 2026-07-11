from unittest.mock import MagicMock

import pytest

from src.action.action_router import ActionRouter, UnsupportedTargetType
from src.perception.ocr import OCRWord


def make_router(with_desktop=False):
    driver = MagicMock()
    mouse_keyboard = MagicMock() if with_desktop else None
    ocr_engine = MagicMock() if with_desktop else None
    router = ActionRouter(
        playwright_driver=driver, mouse_keyboard=mouse_keyboard, ocr_engine=ocr_engine
    )
    return router, driver, mouse_keyboard, ocr_engine


def test_navigate_routes_to_playwright():
    router, driver, _, _ = make_router()
    step = {"action": "navigate", "target_type": "web", "params": {"url": "https://github.com"}}
    outcome = router.execute(step)
    driver.navigate.assert_called_once_with("https://github.com")
    assert outcome["status"] == "executed"


def test_click_routes_to_playwright():
    router, driver, _, _ = make_router()
    step = {"action": "click", "target_type": "web", "params": {"selector": "#star-btn"}}
    router.execute(step)
    driver.click.assert_called_once_with("#star-btn")


def test_type_routes_to_playwright():
    router, driver, _, _ = make_router()
    step = {
        "action": "type",
        "target_type": "web",
        "params": {"selector": "#search", "text": "repo X"},
    }
    router.execute(step)
    driver.type_text.assert_called_once_with("#search", "repo X")


def test_desktop_target_without_backend_raises():
    router, driver, _, _ = make_router(with_desktop=False)
    step = {"action": "click", "target_type": "desktop", "params": {"x": 1, "y": 2}}
    with pytest.raises(UnsupportedTargetType):
        router.execute(step)


def test_desktop_click_with_explicit_coords():
    router, driver, mouse_keyboard, ocr_engine = make_router(with_desktop=True)
    step = {"action": "click", "target_type": "desktop", "params": {"x": 100, "y": 200}}
    outcome = router.execute(step)
    mouse_keyboard.click_at.assert_called_once_with(100, 200)
    assert outcome["status"] == "executed"
    assert outcome["target_type"] == "desktop"


def test_desktop_click_with_target_text_uses_ocr():
    router, driver, mouse_keyboard, ocr_engine = make_router(with_desktop=True)
    mouse_keyboard.screenshot.return_value = "fake_image"
    ocr_engine.read.return_value = [OCRWord(text="Save", bbox=(10, 10, 40, 15), confidence=90.0)]

    step = {"action": "click", "target_type": "desktop", "params": {"target_text": "Save"}}
    router.execute(step)

    ocr_engine.read.assert_called_once_with("fake_image")
    mouse_keyboard.click_at.assert_called_once_with(10 + 20, 10 + 7)


def test_desktop_click_target_text_not_found_raises():
    router, driver, mouse_keyboard, ocr_engine = make_router(with_desktop=True)
    mouse_keyboard.screenshot.return_value = "fake_image"
    ocr_engine.read.return_value = []

    step = {"action": "click", "target_type": "desktop", "params": {"target_text": "Nonexistent"}}
    with pytest.raises(ValueError):
        router.execute(step)


def test_desktop_type_routes_to_mouse_keyboard():
    router, driver, mouse_keyboard, ocr_engine = make_router(with_desktop=True)
    step = {"action": "type", "target_type": "desktop", "params": {"text": "hello"}}
    router.execute(step)
    mouse_keyboard.type_text.assert_called_once_with("hello")


def test_desktop_hotkey_routes_to_mouse_keyboard():
    router, driver, mouse_keyboard, ocr_engine = make_router(with_desktop=True)
    step = {"action": "hotkey", "target_type": "desktop", "params": {"keys": ["ctrl", "s"]}}
    router.execute(step)
    mouse_keyboard.press_hotkey.assert_called_once_with("ctrl", "s")


def test_unknown_web_action_raises():
    router, driver, _, _ = make_router()
    step = {"action": "teleport", "target_type": "web", "params": {}}
    with pytest.raises(ValueError):
        router.execute(step)


def test_unknown_target_type_raises():
    router, driver, _, _ = make_router()
    step = {"action": "click", "target_type": "quantum", "params": {}}
    with pytest.raises(UnsupportedTargetType):
        router.execute(step)
