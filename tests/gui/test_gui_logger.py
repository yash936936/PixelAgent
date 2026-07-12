import tempfile
from pathlib import Path

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateDecision
from src.gui.gui_logger import GuiLogger


def test_log_step_forwards_to_callback():
    captured = []
    logger = GuiLogger(Path(tempfile.mkdtemp()), on_step=captured.append)

    logger.log_step(1, {"action": "navigate"}, {"status": "executed"}, risk=Risk.LOCAL)

    assert len(captured) == 1
    assert captured[0]["step_num"] == 1
    assert captured[0]["risk"] == "local"
    assert captured[0]["audit"]["step_count"] == 1


def test_log_gate_decision_forwards_to_callback():
    captured = []
    logger = GuiLogger(Path(tempfile.mkdtemp()), on_gate=captured.append)

    logger.log_gate_decision(
        1, {"action": "click"}, Risk.EXTERNAL, GateDecision(verdict="approved")
    )

    assert len(captured) == 1
    assert captured[0]["verdict"] == "approved"
    assert captured[0]["risk"] == "external"


def test_still_writes_to_underlying_jsonl_file():
    log_dir = Path(tempfile.mkdtemp())
    logger = GuiLogger(log_dir)
    logger.log_step(1, {"action": "navigate"}, {"status": "executed"})

    assert logger.log_path.exists()
    content = logger.log_path.read_text()
    assert '"type": "step"' in content


def test_callbacks_optional_no_error_when_absent():
    logger = GuiLogger(Path(tempfile.mkdtemp()))
    logger.log_step(1, {"action": "navigate"}, {"status": "executed"})
    logger.log_gate_decision(1, {"action": "click"}, Risk.EXTERNAL, GateDecision(verdict="denied"))
    # No assertion needed beyond "doesn't raise" — this is the no-GUI-attached path.
