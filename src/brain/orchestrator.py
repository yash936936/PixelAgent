"""
The main loop: observe -> plan next step -> classify risk -> gate if needed ->
act -> log -> repeat. Phase 1 scope: browser-only via PlaywrightDriver, no
pixel perception/replanning yet (that's Phase 2 — see docs/PHASES.md Part 2.3).
"""
from __future__ import annotations

from src.action.action_router import ActionRouter
from src.brain.planner import PlannerBackend
from src.brain.risk_classifier import Risk, RiskClassifier
from src.confirmation.gate import ConfirmationGate, GateDecision
from src.observability.logger import Logger


class MaxStepsExceeded(Exception):
    pass


class Orchestrator:
    def __init__(
        self,
        planner: PlannerBackend,
        driver,  # PlaywrightDriver, used for observation (current_url/title)
        action_router: ActionRouter,
        gate: ConfirmationGate,
        logger: Logger,
        max_steps: int = 40,
        risk_classifier: RiskClassifier | None = None,
    ) -> None:
        self._planner = planner
        self._driver = driver
        self._action_router = action_router
        self._gate = gate
        self._logger = logger
        self._max_steps = max_steps
        self._risk_classifier = risk_classifier or RiskClassifier()

    def run_task(self, instruction: str) -> dict:
        history: list[dict] = []
        outcome_status = "incomplete"

        for step_num in range(1, self._max_steps + 1):
            screen_state = self._observe()
            step = self._planner.next_step(instruction, screen_state, history)

            if step["action"] == "done":
                outcome_status = "done"
                self._logger.log_step(step_num, step, {"status": "task_complete"})
                break

            risk = self._risk_classifier.classify(step)

            if self._risk_classifier.needs_confirmation(risk):
                decision = self._gate.request_approval(step, risk)
                self._logger.log_gate_decision(step_num, step, risk, decision)
                if decision.verdict != "approved":
                    outcome_status = f"stopped_{decision.verdict}"
                    break
                if decision.edited_step is not None:
                    step = decision.edited_step

            try:
                action_outcome = self._execute(step)
            except Exception as exc:  # noqa: BLE001 - deliberately broad, logged not swallowed
                self._logger.log_step(step_num, step, {"status": "error", "error": str(exc)})
                outcome_status = "error"
                break

            history.append({"step": step, "outcome": action_outcome})
            self._logger.log_step(step_num, step, action_outcome, risk=risk)
        else:
            raise MaxStepsExceeded(
                f"Task did not complete within {self._max_steps} steps. "
                "See docs/TRD.md §3.1 for the max-step budget rationale."
            )

        result = {"instruction": instruction, "history": history, "status": outcome_status}
        self._logger.log_task_complete(result)
        return result

    def _observe(self) -> dict:
        return {
            "url": self._driver.current_url(),
            "title": self._driver.current_title(),
        }

    def _execute(self, step: dict) -> dict:
        return self._action_router.execute(step)
