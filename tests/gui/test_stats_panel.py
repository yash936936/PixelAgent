from src.gui.widgets.stats_panel import StatsPanel


def test_update_from_audit_sets_values(qapp):
    panel = StatsPanel()
    panel.update_from_audit({"step_count": 5, "llm_calls": 4, "est_cost": 0.0123})

    assert panel._steps_card._value_label.text() == "5"
    assert panel._llm_card._value_label.text() == "4"


def test_reset_zeroes_values(qapp):
    panel = StatsPanel()
    panel.update_from_audit({"step_count": 5, "llm_calls": 4, "est_cost": 0.0123})
    panel.reset()

    assert panel._steps_card._value_label.text() == "0"
    assert panel._llm_card._value_label.text() == "0"


def test_cost_card_removed_per_user_request(qapp):
    panel = StatsPanel()
    assert not hasattr(panel, "_cost_card")
