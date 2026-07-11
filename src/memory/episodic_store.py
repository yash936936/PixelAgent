"""
Episodic memory: persists (instruction, step plan, outcome, timestamp) per
completed task and provides a lookup for "have I done something like this
before?" so the orchestrator can attempt a replay before planning fresh.
See docs/PHASES.md Part 3.1.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instruction TEXT NOT NULL,
    normalized_instruction TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""

# Only these outcomes are considered replayable "successes". Anything else
# (error, stopped_denied, incomplete, ...) is still stored for history/review
# but is never offered as a replay candidate.
_REPLAYABLE_STATUSES = {"done"}

# Below this normalized-text similarity score, a past episode is treated as
# a different task rather than a match. Difflib ratio on whitespace/case
# normalized text is deliberately simple: it needs no embedding model or
# external service, and near-duplicate phrasing is the common case for
# repeated tasks (see Phase 3 success criterion in docs/PHASES.md).
_MATCH_THRESHOLD = 0.82


@dataclass
class Episode:
    id: int
    instruction: str
    steps: list[dict[str, Any]]
    status: str
    created_at: float


def _normalize(instruction: str) -> str:
    return " ".join(instruction.strip().lower().split())


class EpisodicStore:
    """SQLite-backed store, one row per completed task."""

    def __init__(self, db_path: str | Path = "./logs/episodic_memory.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, instruction: str, history: list[dict[str, Any]], status: str) -> int:
        """Persists a completed task. `history` is the orchestrator's
        step/outcome list; only the `step` half of each entry is kept for
        replay purposes -- outcomes are runtime-specific (e.g. actual
        screenshot bytes/paths) and are re-derived fresh on replay rather
        than reused."""
        steps = [entry["step"] for entry in history if "step" in entry]
        cur = self._conn.execute(
            "INSERT INTO episodes (instruction, normalized_instruction, steps_json, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (instruction, _normalize(instruction), json.dumps(steps), status, time.time()),
        )
        self._conn.commit()
        return cur.lastrowid

    def find_match(self, instruction: str) -> Episode | None:
        """Returns the most similar past REPLAYABLE episode, or None if
        nothing clears `_MATCH_THRESHOLD`."""
        normalized = _normalize(instruction)
        best: Episode | None = None
        best_score = 0.0

        placeholders = ",".join("?" for _ in _REPLAYABLE_STATUSES)
        rows = self._conn.execute(
            f"SELECT id, instruction, normalized_instruction, steps_json, status, created_at "
            f"FROM episodes WHERE status IN ({placeholders}) ORDER BY created_at DESC",
            tuple(_REPLAYABLE_STATUSES),
        ).fetchall()

        for row_id, orig_instruction, norm_instruction, steps_json, status, created_at in rows:
            score = SequenceMatcher(None, normalized, norm_instruction).ratio()
            if score > best_score:
                best_score = score
                best = Episode(
                    id=row_id,
                    instruction=orig_instruction,
                    steps=json.loads(steps_json),
                    status=status,
                    created_at=created_at,
                )

        if best is not None and best_score >= _MATCH_THRESHOLD and best.steps:
            return best
        return None

    def all_episodes(self) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT id, instruction, steps_json, status, created_at FROM episodes ORDER BY created_at DESC"
        ).fetchall()
        return [
            Episode(id=r[0], instruction=r[1], steps=json.loads(r[2]), status=r[3], created_at=r[4])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
