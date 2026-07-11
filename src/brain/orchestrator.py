"""
The main loop: observe -> plan next step -> classify risk -> gate if needed ->
act -> verify -> log -> repeat. Phase 2 adds the verify step: screen_diff.py
checks whether an action produced the expected screen change, and
replanner.py is asked for a corrected step on mismatch (bounded by
Replanner's own max_retries). Verification is best-effort: if no screenshot
source is configured, it's skipped rather than failing the task, so this
class still works in Phase-1-only configurations. See docs/PHASES.md Part 1.2
and Part 2.3.
"""
from __future__ import annotations

from pathlib import Path

from src.action.action_router import ActionRouter
from src.action.mouse_keyboard import MouseKeyboard
from src.brain.planner import PlannerBackend
from src.brain.replanner import ReplanExhausted, Replanner
from src.brain.risk_classifier import Risk, RiskClassifier
from src.confirmation.gate import ConfirmationGate, GateDecision
from src.observability.logger import Logger
from src.perception import screen_diff

# Actions that shouldn't be expected to visibly change the screen.
_NO_VISIBLE_CHANGE_ACTIONS = {"screenshot"}


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
        mouse_keyboard: MouseKeyboard | None = None,
        replanner: Replanner | None = None,
        enable_verification: bool = True,
    ) -> None:
        self._planner = planner
        self._driver = driver
        self._action_router = action_router
        self._gate = gate
        self._logger = logger
        self._max_steps = max_steps
        self._risk_classifier = risk_classifier or RiskClassifier()
        self._mouse_keyboard = mouse_keyboard
        self._replanner = replanner
        # Verification only actually runs if we have both a screenshot source
        # and a replanner to hand a mismatch to — otherwise it's a no-op.
        self._enable_verification = enable_verification

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
                action_outcome = self._execute_and_verify(
                    instruction, step, screen_state, history, step_num
                )
            except ReplanExhausted as exc:
                self._logger.log_step(step_num, step, {"status": "replan_exhausted", "error": str(exc)})
                outcome_status = "error"
                break
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

    def _execute_and_verify(
        self,
        instruction: str,
        step: dict,
        screen_state: dict,
        history: list[dict],
        step_num: int,
        attempt: int = 1,
    ) -> dict:
        before_image = self._capture_verification_screenshot()
        outcome = self._execute(step)

        if not self._can_verify(before_image):
            return outcome

        after_image = self._capture_verification_screenshot()
        expect_change = step["action"] not in _NO_VISIBLE_CHANGE_ACTIONS

        if screen_diff.matches_expected(before_image, after_image, expect_change=expect_change):
            return outcome

        # Mismatch: ask the replanner for a corrected step and retry once
        # per Replanner's own max_retries, rather than silently continuing
        # with a step that didn't do what was expected.
        corrected_step = self._replanner.correct(instruction, step, screen_state, history, attempt=attempt)
        self._logger.log_step(
            step_num,
            step,
            {"status": "replanned", "corrected_step": corrected_step, "attempt": attempt},
        )
        return self._execute_and_verify(
            instruction, corrected_step, screen_state, history, step_num, attempt=attempt + 1
        )

    def _can_verify(self, before_image) -> bool:
        return self._replanner is not None and before_image is not None

    def _capture_verification_screenshot(self):
        """Best-effort screenshot for verification. Prefers the desktop
        screenshot backend (covers both web and desktop targets uniformly);
        falls back to the browser's own screenshot; returns None if neither
        is available, which disables verification for this run rather than
        failing the task."""
        if self._mouse_keyboard is not None:
            try:
                return self._mouse_keyboard.screenshot()
            except Exception:  # noqa: BLE001 - verification is best-effort
                return None

        if self._driver is not None:
            try:
                from PIL import Image

                tmp_path = Path("./logs/_verify_tmp.png")
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                self._driver.screenshot(str(tmp_path))
                return Image.open(tmp_path)
            except Exception:  # noqa: BLE001 - verification is best-effort
                return None

        return None
