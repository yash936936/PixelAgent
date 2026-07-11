from src.brain.risk_classifier import Risk, RiskClassifier


def test_local_action_classified_local():
    rc = RiskClassifier()
    step = {"action": "navigate", "description": "Open github.com"}
    assert rc.classify(step) == Risk.LOCAL


def test_star_repo_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Click Star on repo X"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_send_email_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Send the email"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_delete_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Delete the file"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_force_push_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Force push to main"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_empty_step_fails_safe_to_external():
    rc = RiskClassifier()
    step = {"action": "", "description": ""}
    assert rc.classify(step) == Risk.EXTERNAL


def test_needs_confirmation():
    rc = RiskClassifier()
    assert rc.needs_confirmation(Risk.LOCAL) is False
    assert rc.needs_confirmation(Risk.EXTERNAL) is True
    assert rc.needs_confirmation(Risk.DESTRUCTIVE) is True
