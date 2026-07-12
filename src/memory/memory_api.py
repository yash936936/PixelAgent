"""
Unified read/write interface both memory stores go through, so
orchestrator.py and planner.py never touch src/memory/episodic_store.py or
src/memory/semantic_store.py directly. See docs/PHASES.md Part 3.2.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.memory.episodic_store import Episode, EpisodicStore
from src.memory.semantic_store import SemanticStore


class MemoryAPI:
    """Facade over episodic + semantic memory. Construct one instance per
    process (or pass explicit store instances, e.g. in tests) and hand it to
    the orchestrator; nothing else should import the store classes directly.
    """

    def __init__(
        self,
        episodic_store: EpisodicStore | None = None,
        semantic_store: SemanticStore | None = None,
        log_dir: str | Path = "./logs",
    ) -> None:
        log_dir = Path(log_dir)
        self._episodic = episodic_store or EpisodicStore(log_dir / "episodic_memory.db")
        self._semantic = semantic_store or SemanticStore(log_dir / "semantic_memory.db")

    # --- Episodic ---
    def find_replay(self, instruction: str) -> Episode | None:
        """Returns a matching past successful task's step plan, or None."""
        return self._episodic.find_match(instruction)

    def record_task(
        self, instruction: str, history: list[dict[str, Any]], status: str, edited: bool = False
    ) -> int:
        """Persists a just-completed task for future replay lookups. `edited`
        should be True if the user edited any confirmation-gate approval
        during the run -- see `flagged_for_review`."""
        return self._episodic.record(instruction, history, status, edited=edited)

    def flagged_for_review(self):
        """Phase 4: tasks the self-improvement loop should inspect (failed or
        user-edited runs)."""
        return self._episodic.flagged_for_review()

    def all_episodes(self):
        return self._episodic.all_episodes()

    # --- Semantic ---
    def get_preference(self, key: str, default: Any = None) -> Any:
        return self._semantic.get_preference(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        self._semantic.set_preference(key, value)

    def all_preferences(self) -> dict[str, Any]:
        """Read-all for the GUI memory browser (src/gui/widgets/memory_panel.py)."""
        return self._semantic.all_preferences()

    def get_site_quirk(self, site: str, key: str, default: Any = None) -> Any:
        return self._semantic.get_fact(site, key, default)

    def set_site_quirk(self, site: str, key: str, value: Any) -> None:
        self._semantic.set_fact(site, key, value)

    def close(self) -> None:
        self._episodic.close()
        self._semantic.close()
