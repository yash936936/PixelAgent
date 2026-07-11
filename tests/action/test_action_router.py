from unittest.mock import MagicMock

import pytest

from src.action.action_router import ActionRouter, UnsupportedTargetType


def make_router():
    driver = MagicMock()
    router = ActionRouter(playwright_driver=driver)
    return router, driver


def test_navigate_routes_to_playwright():
    router, driver = make_router()
    step = {"action": "navigate", "target_type": "web", "params": {"url": "https://github.com"}}
    outcome = router.execute(step)
    driver.navigate.assert_called_once_with("https://github.com")
    assert outcome["status"] == "executed"


def test_click_routes_to_playwright():
    router, driver = make_router()
    step = {"action": "click", "target_type": "web", "params": {"selector": "#star-btn"}}
    router.execute(step)
    driver.click.assert_called_once_with("#star-btn")


def test_type_routes_to_playwright():
    router, driver = make_router()
    step = {
        "action": "type",
        "target_type": "web",
        "params": {"selector": "#search", "text": "repo X"},
    }
    router.execute(step)
    driver.type_text.assert_called_once_with("#search", "repo X")


def test_desktop_target_not_supported_in_phase1():
    router, driver = make_router()
    step = {"action": "click", "target_type": "desktop", "params": {}}
    with pytest.raises(UnsupportedTargetType):
        router.execute(step)


def test_unknown_web_action_raises():
    router, driver = make_router()
    step = {"action": "teleport", "target_type": "web", "params": {}}
    with pytest.raises(ValueError):
        router.execute(step)
