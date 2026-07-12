from PySide6.QtCore import Qt, QThread

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateContext, GateDecision
from src.gui.worker import GateBridge


def test_gate_bridge_round_trip_across_real_thread(qapp):
    bridge = GateBridge()
    results = []

    def on_request(step, risk_value, context):
        assert risk_value == "external"
        bridge.set_pending_decision(GateDecision(verdict="approved"))

    bridge.request_confirmation.connect(on_request, Qt.BlockingQueuedConnection)

    class Worker(QThread):
        def run(self):
            decision = bridge.ask({"action": "click"}, Risk.EXTERNAL, GateContext())
            results.append(decision.verdict)

    worker = Worker()
    worker.finished.connect(qapp.quit)
    worker.start()
    qapp.exec()
    worker.wait(2000)

    assert results == ["approved"]


def test_gate_bridge_prompt_fn_matches_gate_contract(qapp):
    """ConfirmationGate calls prompt_fn(step, risk, context) — verify
    GateBridge.prompt_fn accepts exactly that signature."""
    bridge = GateBridge()
    bridge.set_pending_decision(GateDecision(verdict="denied"))

    # Connect a no-op handler so .emit() doesn't hang waiting on nothing.
    def on_request(step, risk_value, context):
        pass

    bridge.request_confirmation.connect(on_request, Qt.DirectConnection)

    decision = bridge.prompt_fn({"action": "click"}, Risk.EXTERNAL, GateContext())
    assert decision.verdict == "denied"
