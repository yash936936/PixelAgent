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


# --- Phase 5 hardening: expanded rule-table cases -------------------------

def test_delete_account_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Delete account permanently"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_format_drive_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "run", "description": "Format drive C:"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_delete_branch_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Delete branch feature/x on GitHub"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_cancel_subscription_classified_destructive():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Cancel subscription for this account"}
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_book_reservation_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Book a table for 7pm"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_direct_message_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Send a DM to the user"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_authorize_app_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Authorize app to access account"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_place_order_classified_external():
    rc = RiskClassifier()
    step = {"action": "click", "description": "Place order for the cart items"}
    assert rc.classify(step) == Risk.EXTERNAL


def test_read_only_check_for_delete_button_not_escalated():
    rc = RiskClassifier()
    step = {"action": "inspect", "description": "Check whether the delete button exists on the page"}
    assert rc.classify(step) == Risk.LOCAL


def test_read_only_guard_does_not_suppress_real_click():
    rc = RiskClassifier()
    step = {
        "action": "click",
        "description": "Check if the delete button works, then click delete",
    }
    assert rc.classify(step) == Risk.DESTRUCTIVE


def test_review_document_not_misclassified_external():
    rc = RiskClassifier()
    step = {"action": "read", "description": "Review the document contents"}
    assert rc.classify(step) == Risk.LOCAL
