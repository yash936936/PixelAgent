"""
The main loop: observe -> boundary-check -> plan next step -> classify risk
(keyword-based, with an LLM second opinion for anything the keyword filter
found no signal on) -> gate if needed -> act -> verify -> log -> repeat.
Phase 2 adds the verify step: screen_diff.py checks whether an action
produced the expected screen change, and replanner.py is asked for a
corrected step on mismatch (bounded by Replanner's own max_retries).
Verification is best-effort: if no screenshot source is configured, it's
skipped rather than failing the task -- but every time it's skipped due to
an actual failure (not just "not configured"), that's now logged as an
event rather than silently disappearing (fix for a gap flagged in review:
verification could previously fail silently with zero trace). Phase 3 adds
an episodic replay attempt before fresh planning: if memory_api.py finds a
matching past successful task, its step plan is replayed (still gated/
verified exactly like a freshly-planned step) instead of paying for a
planner call per step; any replay failure falls back to fresh planning for
the remaining steps rather than failing the task. Phase 4 wires in the
self-improvement loop: whenever the user edits a step before approving it,
replanner.py's review_and_learn() writes the correction to semantic memory,
and every completed task now records whether any edit happened so
episodic_store.py's flagged_for_review() can surface it later. Post-Phase-5
hardening (see docs/DECISIONS.md): every step is now also checked against
brain/boundary_guard.py's deterministic hard-boundary patterns *before*
risk classification -- this runs regardless of what the LLM planner
proposed and cannot be gated/edited around, since context.md's hard
boundaries are non-negotiable, not just another risk tier. See
docs/PHASES.md Part 1.2, Part 2.3, Part 3.1, and Phase 4.
"""
from __future__ import annotations

from pathlib import Path

from src.action.action_router import ActionRouter
from src.action.mouse_keyboard import MouseKeyboard
from src.brain import boundary_guard
from src.brain.boundary_guard import BoundaryBlocked
from src.brain.planner import PlannerBackend
from src.brain.replanner import ReplanExhausted, Replanner
from src.brain.risk_classifier import Risk, RiskClassifier
from src.confirmation.gate import ConfirmationGate, GateContext, GateDecision
from src.memory.memory_api import MemoryAPI
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
        memory: MemoryAPI | None = None,
        log_dir: Path | None = None,
        llm_risk_judge=None,
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
        # Episodic replay only actually runs if a MemoryAPI is supplied —
        # otherwise every task is freshly planned, matching Phase 1/2 behavior.
        self._memory = memory
        # Config-sourced log dir for the verification-screenshot scratch
        # file (fix for a gap flagged in review: this used to be a
        # hardcoded "./logs/..." path, bypassing config.py entirely, which
        # violated the project's own "nothing hardcodes config elsewhere"
        # rule and risked clobbering across concurrent runs sharing a CWD).
        self._log_dir = Path(log_dir) if log_dir is not None else Path("./logs")
        # Optional LLM second opinion for steps the keyword-based
        # RiskClassifier found no signal on at all (see
        # risk_classifier.py's classify_with_confidence() and
        # risk_llm_judge.py). None means "no LLM judge configured" -- the
        # system still works exactly as before, just without the second
        # opinion, so this is additive rather than a hard requirement.
        self._llm_risk_judge = llm_risk_judge

    def run_task(self, instruction: str) -> dict:
        history: list[dict] = []
        outcome_status = "incomplete"
        start_step = 1
        any_edits = False

        if self._memory is not None:
            episode = self._memory.find_replay(instruction)
            if episode is not None:
                replayed, replay_ok, replay_edited = self._replay_episode(instruction, episode, history)
                any_edits = any_edits or replay_edited
                start_step = replayed + 1
                if replay_ok:
                    outcome_status = "done"
                    self._logger.log_event(
                        replayed,
                        {"status": "task_complete_via_replay", "source_episode_id": episode.id},
                    )
                    result = {"instruction": instruction, "history": history, "status": outcome_status}
                    self._logger.log_task_complete(result)
                    self._memory.record_task(instruction, history, outcome_status, edited=any_edits)
                    return result
                # Replay stopped partway (gate denial, execution error, or
                # exhausted replan) -- fall through to fresh planning for the
                # remaining steps, using what replay already executed as
                # context/history rather than starting over from scratch.

        for step_num in range(start_step, self._max_steps + 1):
            screen_state = self._observe()
            step = self._planner.next_step(instruction, screen_state, history)

            if step["action"] == "done":
                outcome_status = "done"
                self._logger.log_step(
                    step_num, step, {"status": "task_complete"}, llm_call=True, cost=self._planner_cost()
                )
                break

            try:
                self._check_boundary(step_num, step)
            except BoundaryBlocked as exc:
                outcome_status = "blocked_hard_boundary"
                self._logger.log_step(step_num, step, {"status": "hard_boundary_blocked", "error": str(exc)})
                break

            risk = self._classify_risk(step_num, step)

            if self._risk_classifier.needs_confirmation(risk):
                decision = self._gate.request_approval(step, risk, self._gate_context())
                self._logger.log_gate_decision(step_num, step, risk, decision)
                if decision.verdict != "approved":
                    outcome_status = f"stopped_{decision.verdict}"
                    break
                if decision.edited_step is not None:
                    any_edits = True
                    if self._replanner is not None:
                        self._replanner.review_and_learn(
                            instruction, step, decision.edited_step, memory=self._memory
                        )
                    step = decision.edited_step

            try:
                action_outcome = self._execute_and_verify(
                    instruction, step, screen_state, history, step_num
                )
            except BoundaryBlocked as exc:
                self._logger.log_step(step_num, step, {"status": "hard_boundary_blocked", "error": str(exc)})
                outcome_status = "blocked_hard_boundary"
                break
            except ReplanExhausted as exc:
                self._logger.log_step(step_num, step, {"status": "replan_exhausted", "error": str(exc)})
                outcome_status = "error"
                break
            except Exception as exc:  # noqa: BLE001 - deliberately broad, logged not swallowed
                self._logger.log_step(step_num, step, {"status": "error", "error": str(exc)})
                outcome_status = "error"
                break

            history.append({"step": step, "outcome": action_outcome})
            self._logger.log_step(
                step_num, step, action_outcome, risk=risk, llm_call=True, cost=self._planner_cost()
            )
        else:
            raise MaxStepsExceeded(
                f"Task did not complete within {self._max_steps} steps. "
                "See docs/TRD.md §3.1 for the max-step budget rationale."
            )

        result = {"instruction": instruction, "history": history, "status": outcome_status}
        self._logger.log_task_complete(result)
        if self._memory is not None:
            self._memory.record_task(instruction, history, outcome_status, edited=any_edits)
        return result

    def _replay_episode(
        self, instruction: str, episode, history: list[dict]
    ) -> tuple[int, bool, bool]:
        """Attempts to replay a matched past episode's step plan verbatim,
        skipping fresh LLM planning calls for as many steps as replay stays
        valid. Each replayed step still goes through the same risk
        classification, confirmation gate, and verification as a freshly
        planned step -- replay is a planning shortcut, never a safety
        shortcut. Returns (steps_replayed, fully_succeeded, any_edits); on
        any gate denial, execution error, or exhausted replan, stops early
        so the caller can fall back to fresh planning for the rest of the
        task. A step actually executed during replay is logged with
        llm_call=False, since no planner call was made for it -- this is
        what makes the Phase 3/4 "fewer LLM calls on repeat tasks" success
        criterion visible in the trace log's LoopAudit summary."""
        any_edits = False
        self._logger.log_event(
            0, {"status": "replay_attempt", "source_episode_id": episode.id, "match_score": episode.match_score}
        )

        for idx, step in enumerate(episode.steps, start=1):
            screen_state = self._observe()

            try:
                self._check_boundary(idx, step)
            except BoundaryBlocked:
                return idx - 1, False, any_edits

            risk = self._classify_risk(idx, step)

            if self._risk_classifier.needs_confirmation(risk):
                decision = self._gate.request_approval(step, risk, self._gate_context())
                self._logger.log_gate_decision(idx, step, risk, decision)
                if decision.verdict != "approved":
                    return idx - 1, False, any_edits
                if decision.edited_step is not None:
                    any_edits = True
                    if self._replanner is not None:
                        self._replanner.review_and_learn(
                            instruction, step, decision.edited_step, memory=self._memory
                        )
                    step = decision.edited_step

            try:
                outcome = self._execute_and_verify(instruction, step, screen_state, history, idx)
            except ReplanExhausted as exc:
                self._logger.log_step(idx, step, {"status": "replay_replan_exhausted", "error": str(exc)})
                return idx - 1, False, any_edits
            except Exception as exc:  # noqa: BLE001 - replay is best-effort, fall back to fresh planning
                self._logger.log_step(idx, step, {"status": "replay_error", "error": str(exc)})
                return idx - 1, False, any_edits

            history.append({"step": step, "outcome": outcome})
            self._logger.log_step(idx, step, outcome, risk=risk, llm_call=False)

        return len(episode.steps), True, any_edits

    def _planner_cost(self) -> float:
        """Reads the real per-call cost the active PlannerBackend recorded
        for its most recent next_step() call (fix for the gap flagged in
        review: LoopAudit.est_cost was always 0.0 because nothing computed
        or passed a real cost anywhere). Defaults to 0.0 for any planner
        that doesn't expose last_call_cost (e.g. LocalPlanner, or a mock in
        tests) rather than raising, so this is purely additive."""
        return getattr(self._planner, "last_call_cost", 0.0) or 0.0

    def _check_boundary(self, step_num: int, step: dict) -> None:
        """Deterministic hard-boundary check, independent of the LLM
        planner's own judgment (fix for the gap flagged in review: the
        boundaries in context.md were previously enforced only by hoping
        the planner LLM refused on its own). Raises BoundaryBlocked, which
        the caller does not catch alongside ordinary execution errors --
        a tripped hard boundary halts the task outright rather than being
        offered to the confirmation gate, since it's non-negotiable, not
        just another risk tier a user could approve past."""
        violation = boundary_guard.check(step)
        if violation is not None:
            self._logger.log_event(
                step_num,
                {
                    "status": "hard_boundary_blocked",
                    "boundary": violation.boundary.value,
                    "matched_phrase": violation.matched_phrase,
                    "step": step,
                },
            )
            raise BoundaryBlocked(violation)

    def _classify_risk(self, step_num: int, step: dict) -> Risk:
        """Keyword classification, with an LLM second opinion consulted
        only when the keyword filter found no signal at all (fix for the
        gap flagged in review: this fallback was previously described in
        risk_classifier.py's docstring but never actually implemented or
        called anywhere). The LLM can only escalate Local -> External/
        Destructive here, never downgrade a keyword-matched result, and any
        LLM failure fails safe to the keyword-based answer -- see
        risk_llm_judge.py's docstring for the full rationale."""
        risk, confident = self._risk_classifier.classify_with_confidence(step)

        if confident or self._llm_risk_judge is None:
            return risk

        llm_opinion = self._llm_risk_judge(step)
        if llm_opinion is not None and llm_opinion != Risk.LOCAL:
            self._logger.log_event(
                step_num,
                {
                    "status": "llm_risk_escalation",
                    "keyword_result": risk.value,
                    "llm_result": llm_opinion.value,
                    "step": step,
                },
            )
            return llm_opinion

        return risk

    def _observe(self) -> dict:
        return {
            "url": self._driver.current_url(),
            "title": self._driver.current_title(),
        }

    def _gate_context(self) -> GateContext:
        """Builds the extra prompt context gate.py/prompt_ui.py can now
        display (fix for the gap flagged in review — see gate.py's and
        prompt_ui.py's docstrings). Best-effort: any failure to read a
        screenshot or profile name just omits that field rather than
        blocking the confirmation prompt on it."""
        screenshot_path = None
        try:
            img = self._capture_verification_screenshot() if self._replanner is not None else None
            if img is not None:
                path = self._log_dir / f"_gate_context_{id(self)}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                img.save(path)
                screenshot_path = str(path)
        except Exception:  # noqa: BLE001 - purely cosmetic context for the prompt
            screenshot_path = None

        account_profile = None
        try:
            account_profile = getattr(self._driver, "profile_name", None)
        except Exception:  # noqa: BLE001
            account_profile = None

        return GateContext(screenshot_path=screenshot_path, account_profile=account_profile)

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
        before_image = self._capture_verification_screenshot() if self._replanner is not None else None
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
        is available or both fail, which disables verification for this run
        rather than failing the task. Any failure is now logged as an event
        (fix for a gap flagged in review: this used to swallow every
        exception silently, so a whole task could run completely
        unverified with zero trace of why) -- the uses of this method that
        matter for correctness are unaffected, but a developer reading the
        trace can now actually tell verification was skipped and why,
        instead of inferring it from the absence of "replanned" events."""
        if self._mouse_keyboard is not None:
            try:
                return self._mouse_keyboard.screenshot()
            except Exception as exc:  # noqa: BLE001 - verification is best-effort
                self._logger.log_event(
                    0, {"status": "verification_screenshot_failed", "source": "mouse_keyboard", "error": str(exc)}
                )
                return None

        if self._driver is not None:
            try:
                from PIL import Image

                tmp_path = self._log_dir / f"_verify_tmp_{id(self)}.png"
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                self._driver.screenshot(str(tmp_path))
                return Image.open(tmp_path)
            except Exception as exc:  # noqa: BLE001 - verification is best-effort
                self._logger.log_event(
                    0, {"status": "verification_screenshot_failed", "source": "playwright_driver", "error": str(exc)}
                )
                return None

        self._logger.log_event(0, {"status": "verification_unavailable", "reason": "no screenshot source configured"})
        return None
