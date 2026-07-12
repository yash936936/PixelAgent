"""
Thin subclass of observability/logger.py's Logger that forwards every write
to plain Python callbacks (on_step / on_gate), so the GUI's trace panel can
update live without src/observability/logger.py itself taking a Qt
dependency — Logger stays usable from the CLI (main.py) exactly as before.
The callbacks are invoked on the worker thread; TaskWorker's caller connects
the corresponding Qt signals with Qt.QueuedConnection (Qt's default for
cross-thread signal/slot) so the actual UI update happens safely on the GUI
thread.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.observability.logger import Logger


class GuiLogger(Logger):
    def __init__(
        self,
        log_dir: Path,
        on_step: Callable[[dict], None] | None = None,
        on_gate: Callable[[dict], None] | None = None,
    ) -> None:
        super().__init__(log_dir)
        self._on_step = on_step
        self._on_gate = on_gate

    def log_step(self, step_num, step, outcome, risk=None, llm_call=True, cost=0.0) -> None:
        super().log_step(step_num, step, outcome, risk=risk, llm_call=llm_call, cost=cost)
        if self._on_step:
            self._on_step(
                {
                    "step_num": step_num,
                    "step": step,
                    "outcome": outcome,
                    "risk": risk.value if risk else None,
                    "audit": self.audit.summary(),
                }
            )

    def log_gate_decision(self, step_num, step, risk, decision) -> None:
        super().log_gate_decision(step_num, step, risk, decision)
        if self._on_gate:
            self._on_gate(
                {
                    "step_num": step_num,
                    "step": step,
                    "risk": risk.value,
                    "verdict": decision.verdict,
                    "edited": decision.edited_step is not None,
                }
            )
