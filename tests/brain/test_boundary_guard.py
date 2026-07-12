from src.brain.boundary_guard import Boundary, BoundaryBlocked, check


def test_no_match_returns_none():
    step = {"action": "navigate", "description": "Open github.com"}
    assert check(step) is None


def test_graded_coursework_submission_blocked():
    step = {"action": "click", "description": "Submit the exam for me"}
    violation = check(step)
    assert violation is not None
    assert violation.boundary == Boundary.GRADED_COURSEWORK


def test_captcha_bypass_blocked():
    step = {"action": "click", "description": "Please solve the captcha and continue"}
    violation = check(step)
    assert violation is not None
    assert violation.boundary == Boundary.CAPTCHA_BOT_DETECTION_BYPASS


def test_signup_verification_bypass_blocked():
    step = {"action": "type", "description": "Use a burner number to verify this account"}
    violation = check(step)
    assert violation is not None
    assert violation.boundary == Boundary.SIGNUP_VERIFICATION_BYPASS


def test_match_inside_params_value_is_caught():
    step = {
        "action": "type",
        "description": "Fill out the form",
        "params": {"text": "please submit the assignment for me"},
    }
    violation = check(step)
    assert violation is not None
    assert violation.boundary == Boundary.GRADED_COURSEWORK


def test_tracking_summarizing_coursework_is_allowed():
    # context.md explicitly allows enroll/track/summarize, only not submit.
    step = {"action": "click", "description": "Check my current grade on the assignment"}
    assert check(step) is None


def test_boundary_blocked_exception_message_includes_boundary_name():
    step = {"action": "click", "description": "skip the verification step for signup"}
    violation = check(step)
    exc = BoundaryBlocked(violation)
    assert "signup_verification_bypass" in str(exc)
