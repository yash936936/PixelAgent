from src.confirmation.gate import GateContext
from src.gui.widgets.confirmation_dialog import ConfirmationDialog


def _step():
    return {"action": "click", "description": "Star the repo", "params": {"selector": "#star"}}


def test_dialog_defaults_to_denied_if_never_interacted(qapp):
    dialog = ConfirmationDialog(_step(), "external")
    assert dialog.verdict == "denied"
    assert dialog.decision.verdict == "denied"


def test_approve_sets_approved_verdict(qapp):
    dialog = ConfirmationDialog(_step(), "external")
    dialog._on_approve()
    assert dialog.verdict == "approved"
    assert dialog.decision.verdict == "approved"


def test_deny_sets_denied_verdict(qapp):
    dialog = ConfirmationDialog(_step(), "external")
    dialog._on_deny()
    assert dialog.verdict == "denied"


def test_edit_box_populates_edited_step_when_visible(qapp):
    dialog = ConfirmationDialog(_step(), "external")
    dialog._toggle_edit()
    dialog._edit_box.setPlainText("Star a different repo instead")
    dialog._on_approve()
    assert dialog.edited_step is not None
    assert dialog.edited_step["description"] == "Star a different repo instead"


def test_destructive_requires_confirm_input_field_present(qapp):
    dialog = ConfirmationDialog(_step(), "destructive")
    assert dialog._confirm_input is not None
    dialog._confirm_input.setText("CONFIRM")
    dialog._on_approve()
    assert dialog.raw_user_input == "CONFIRM"


def test_external_has_no_confirm_input_field(qapp):
    dialog = ConfirmationDialog(_step(), "external")
    assert dialog._confirm_input is None


def test_dialog_context_shown_when_provided(qapp):
    ctx = GateContext(screenshot_path="./logs/shot.png", account_profile="Work")
    dialog = ConfirmationDialog(_step(), "external", context=ctx)
    assert dialog._context.account_profile == "Work"
    assert dialog._context.screenshot_path == "./logs/shot.png"
