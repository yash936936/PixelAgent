"""
Structured logger: every plan, action, screenshot reference, gate decision,
and outcome, with timestamps, written to the local log directory from
config.py. Also includes LoopAudit (docs/CODE_LOGIC.md §9) for step-count /
LLM-call / cost tracking, supporting the max-step budget in docs/TRD.md §3.1.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.brain.risk_classifier import Risk


@dataclass
class LoopAudit:
    step_count: int = 0
    llm_calls: int = 0
    est_cost: float = 0.0

    def record_step(self, llm_call: bool = True, cost: float = 0.0) -> None:
        self.step_count += 1
        if llm_call:
            self.llm_calls += 1
            self.est_cost += cost

    def summary(self) -> dict:
        return asdict(self)


class Logger:
    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._task_id = datetime.now(timezone.utc).strftime("task_%Y%m%dT%H%M%S")
        self._log_path = self._log_dir / f"{self._task_id}.jsonl"
        self.audit = LoopAudit()

    def _write(self, record: dict) -> None:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def log_step(self, step_num: int, step: dict, outcome: dict, risk: Risk | None = None) -> None:
        self.audit.record_step(llm_call=True)
        self._write(
            {
                "type": "step",
                "step_num": step_num,
                "step": step,
                "outcome": outcome,
                "risk": risk.value if risk else None,
            }
        )

    def log_gate_decision(self, step_num: int, step: dict, risk: Risk, decision) -> None:
        self._write(
            {
                "type": "gate_decision",
                "step_num": step_num,
                "step": step,
                "risk": risk.value,
                "verdict": decision.verdict,
                "edited": decision.edited_step is not None,
            }
        )

    def log_task_complete(self, result: dict) -> None:
        self._write({"type": "task_complete", "result": result, "audit": self.audit.summary()})

    @property
    def log_path(self) -> Path:
        return self._log_path
