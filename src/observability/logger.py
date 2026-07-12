"""
Structured logger: every plan, action, screenshot reference, gate decision,
and outcome, with timestamps, written to the local log directory from
config.py. Also includes LoopAudit (docs/CODE_LOGIC.md §9) for step-count /
LLM-call / cost tracking, supporting the max-step budget in docs/TRD.md §3.1.
Phase 4 refines LoopAudit accuracy: log_step() now takes an explicit
llm_call flag so episodic-replay steps (Phase 3, no planner call made) don't
inflate the llm_calls count, and log_event() covers meta/marker records
(e.g. "replay started") that shouldn't count as a step at all -- this is
what makes the Phase 3/4 "fewer planning calls on repeat tasks" success
criterion actually measurable from the trace log.

Fix for a gap flagged in review: docs/TRD.md §4 requires "no plaintext
storage of user credentials," but nothing anywhere ever redacted anything --
a step that typed a password would have written it verbatim into this
plaintext .jsonl file forever. _redact_step() now masks any params value
whose key looks like a credential field (password, secret, token, api_key,
etc.) before it's written, in every method that logs a step. This is a
best-effort heuristic (key-name matching), not a guarantee -- it can't catch
a credential embedded in a differently-named field or inside free-text --
so it doesn't replace avoiding credential entry via this agent where
possible, but it closes the most common, easily-avoidable leak.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.brain.risk_classifier import Risk

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|credential|auth|ssn|social[_-]?security|"
    r"credit[_-]?card|card[_-]?number|cvv|pin)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


def _redact_step(step: dict | None) -> dict | None:
    """Returns a deep copy of `step` with any params value whose key looks
    like a credential/secret field replaced with a fixed redaction marker.
    Never mutates the caller's original step dict."""
    if not isinstance(step, dict):
        return step

    redacted = copy.deepcopy(step)
    params = redacted.get("params")
    if isinstance(params, dict):
        for key in list(params.keys()):
            if _SENSITIVE_KEY_PATTERN.search(str(key)):
                params[key] = _REDACTED
    return redacted


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

    def log_step(
        self, step_num: int, step: dict, outcome: dict, risk: Risk | None = None,
        llm_call: bool = True, cost: float = 0.0,
    ) -> None:
        self.audit.record_step(llm_call=llm_call, cost=cost)
        self._write(
            {
                "type": "step",
                "step_num": step_num,
                "step": _redact_step(step),
                "outcome": _redact_step(outcome),
                "risk": risk.value if risk else None,
                "llm_call": llm_call,
            }
        )

    def log_event(self, step_num: int, payload: dict) -> None:
        """For meta/marker records that aren't a real Brain step and should
        never affect LoopAudit's step/LLM-call counters (e.g. "replay
        started"). Any embedded "step" key is redacted the same way
        log_step() redacts it, since events (e.g. hard_boundary_blocked)
        can carry a full step payload too."""
        payload = dict(payload)
        if "step" in payload:
            payload["step"] = _redact_step(payload["step"])
        self._write({"type": "event", "step_num": step_num, **payload})

    def log_gate_decision(self, step_num: int, step: dict, risk: Risk, decision) -> None:
        self._write(
            {
                "type": "gate_decision",
                "step_num": step_num,
                "step": _redact_step(step),
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
