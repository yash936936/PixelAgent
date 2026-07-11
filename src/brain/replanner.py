"""
Triggered when screen_diff.py shows an action didn't produce the expected
state; asks the planner for a corrected next step instead of blindly
continuing. Phase 4 extends this with review_and_learn: when a user edits a
proposed confirmation-gate step before approving it, that correction is
written back to semantic memory (via memory_api.py) so future proposals for
the same action type start from the corrected version instead of repeating
the same mistake. See docs/PHASES.md Part 2.3 and the Phase 4 update, and
docs/CODE_LOGIC.md §11.
"""
from __future__ import annotations

from typing import Any

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

    def review_and_learn(
        self,
        instruction: str,
        original_step: dict[str, Any],
        edited_step: dict[str, Any],
        memory=None,
    ) -> None:
        """Phase 4 hook (docs/CODE_LOGIC.md §11): compares a proposed step to
        what the user actually approved after editing, and writes the
        correction to semantic memory so it's available the next time a
        similar step is proposed. No-op if no memory (MemoryAPI) is
        supplied, so this can be called safely even when memory is
        disabled. The namespace is the action type (e.g. "click"), scoped
        further by the edited step's own target/selector where present, so
        corrections for different actions never overwrite each other."""
        if memory is None:
            return
        if original_step == edited_step:
            return

        action = original_step.get("action", "unknown_action")
        target_key = (
            original_step.get("params", {}).get("selector")
            or original_step.get("params", {}).get("url")
            or "default"
        )
        memory.set_site_quirk(
            f"corrections:{action}",
            target_key,
            {
                "instruction": instruction,
                "original_step": original_step,
                "edited_step": edited_step,
            },
        )
