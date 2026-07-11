"""
Triggered when screen_diff.py shows an action didn't produce the expected
state; asks the planner for a corrected next step instead of blindly
continuing. See docs/PHASES.md Part 2.3 (Phase 4 extends this with
review_and_learn, per docs/CODE_LOGIC.md §11).
"""
from __future__ import annotations

from src.brain.planner import PlannerBackend


class ReplanExhausted(Exception):
    pass


class Replanner:
    def __init__(self, planner: PlannerBackend, max_retries: int = 2) -> None:
        self._planner = planner
        self._max_retries = max_retries

    def correct(
        self,
        instruction: str,
        failed_step: dict,
        screen_state: dict,
        history: list[dict],
        attempt: int = 1,
    ) -> dict:
        if attempt > self._max_retries:
            raise ReplanExhausted(
                f"Step did not produce the expected screen change after {self._max_retries} "
                f"replanning attempts: {failed_step}"
            )

        correction_note = {
            "step": failed_step,
            "outcome": {
                "status": "unexpected_screen_state",
                "note": (
                    "The previous step did not produce the expected screen change. "
                    "Propose a corrected next step that accounts for this."
                ),
            },
        }
        corrected_history = history + [correction_note]
        return self._planner.next_step(instruction, screen_state, corrected_history)

    def review_and_learn(self, failed_or_edited_task: dict, semantic_store=None) -> None:
        """Phase 4 hook (docs/CODE_LOGIC.md §11) — compares a proposed step to
        what the user actually approved/edited and writes the correction to
        semantic memory. No-op until Phase 3's semantic_store.py exists, so
        this can be called safely from Phase 2 onward without error."""
        if semantic_store is None:
            return
        if failed_or_edited_task.get("user_edit"):
            semantic_store.write_fact(
                subject=failed_or_edited_task.get("task_type", "unknown_task"),
                fact={"correction": failed_or_edited_task["user_edit"]},
            )
