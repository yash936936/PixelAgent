from src.gui.widgets.trace_panel import TracePanel


def test_add_step_creates_a_card(qapp):
    panel = TracePanel()
    panel.add_step(
        {
            "step_num": 1,
            "step": {"action": "navigate", "description": "go to site"},
            "outcome": {"status": "executed"},
            "risk": "local",
        }
    )
    # 1 card + the trailing stretch item
    assert panel._list_layout.count() == 2


def test_add_gate_decision_creates_a_card(qapp):
    panel = TracePanel()
    panel.add_gate_decision(
        {
            "step_num": 2,
            "step": {"action": "click", "description": "star it"},
            "risk": "external",
            "verdict": "approved",
            "edited": False,
        }
    )
    assert panel._list_layout.count() == 2


def test_error_status_overrides_risk_to_error_card(qapp):
    panel = TracePanel()
    panel.add_step(
        {
            "step_num": 1,
            "step": {"action": "click", "description": "broken"},
            "outcome": {"status": "error", "error": "boom"},
            "risk": "local",
        }
    )
    assert panel._list_layout.count() == 2


def test_clear_removes_all_cards_but_keeps_stretch(qapp):
    panel = TracePanel()
    panel.add_step(
        {"step_num": 1, "step": {"action": "navigate", "description": "go"},
         "outcome": {"status": "executed"}, "risk": "local"}
    )
    panel.add_step(
        {"step_num": 2, "step": {"action": "navigate", "description": "go again"},
         "outcome": {"status": "executed"}, "risk": "local"}
    )
    assert panel._list_layout.count() == 3
    panel.clear()
    assert panel._list_layout.count() == 1


def test_add_task_complete_done_status(qapp):
    panel = TracePanel()
    panel.add_task_complete({"status": "done", "instruction": "do the thing"})
    assert panel._list_layout.count() == 2
