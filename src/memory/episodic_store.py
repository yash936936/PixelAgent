"""
Episodic memory: persists (instruction, step plan, outcome, timestamp) per
completed task and provides a lookup for "have I done something like this
before?" so the orchestrator can attempt a replay before planning fresh.
Phase 4 adds a review pass (`flagged_for_review`) that surfaces failed or
user-edited tasks for the self-improvement loop to inspect -- an `edited`
flag is recorded per task (set when the user edited any confirmation-gate
approval during the run) alongside the existing status. See docs/PHASES.md
Part 3.1 and the Phase 4 episodic_store.py update.

Fix for a real, serious bug found live on 2026-08-01 (docs/DECISIONS.md):
find_match() replays a matched episode's stored steps VERBATIM, completely
bypassing the planner -- which means it also bypasses any prompt/schema
fix made to the planner after that episode was recorded. Concretely: the
"type into Notepad" focus-verification fix (mouse_keyboard.py's
expect_window_contains) was added, but a stale episode recorded BEFORE
that fix (with no expect_window_contains in its stored step) was replayed
on the very next run with a matching instruction (match_score 1.0),
resurrecting the exact bug the fix was meant to close -- the test message
typed into the terminal again, because the replayed step simply didn't
have the new safety field to check. Fixed with a STEP_SCHEMA_VERSION gate:
every recorded episode is stamped with the schema version active when it
was recorded, and find_match() only ever considers episodes stamped with
the CURRENT version as replay candidates. Older episodes remain in the
database (still visible via all_episodes()/flagged_for_review() for
history/review) but are never replayed -- forcing a fresh plan through the
current (fixed) planner/prompt instead of silently resurrecting
pre-fix behavior. Bump STEP_SCHEMA_VERSION whenever a future change adds or
changes a safety-relevant field in the step schema.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# Bump this whenever a change to the step schema is safety-relevant enough
# that an old, differently-shaped step should never be silently replayed
# instead of re-planned. Current value bumped to 2 on 2026-08-01 for the
# expect_window_contains addition (see module docstring above) -- any
# episode recorded under version 1 is permanently excluded from replay.
STEP_SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instruction TEXT NOT NULL,
    normalized_instruction TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    status TEXT NOT NULL,
    edited INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1
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
    edited: bool = False
    # Fix for a gap flagged in review: replay was previously an all-or-
    # nothing decision below _MATCH_THRESHOLD with the actual similarity
    # score thrown away, so nothing in the trace log could ever show how
    # confident a given replay was -- a borderline 0.83 match and a
    # near-exact 0.99 match were indistinguishable after the fact. Now
    # carried through so orchestrator.py can log it.
    match_score: float = 0.0


def _normalize(instruction: str) -> str:
    return " ".join(instruction.strip().lower().split())


class EpisodicStore:
    """SQLite-backed store, one row per completed task."""

    def __init__(self, db_path: str | Path = "./logs/episodic_memory.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(_SCHEMA)
        self._migrate_add_schema_version_column()
        self._conn.commit()

    def _migrate_add_schema_version_column(self) -> None:
        """A database created before this fix won't have schema_version at
        all. ALTER TABLE ADD COLUMN with a DEFAULT backfills existing rows
        as version 1 -- which is exactly correct, since every episode
        recorded before this fix existed IS schema version 1 (no
        expect_window_contains field), and must never be replayed under
        the current version. Safe to call on every startup: ignores the
        error if the column already exists."""
        existing_columns = {row[1] for row in self._conn.execute("PRAGMA table_info(episodes)")}
        if "schema_version" not in existing_columns:
            self._conn.execute("ALTER TABLE episodes ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")

    def record(
        self, instruction: str, history: list[dict[str, Any]], status: str, edited: bool = False
    ) -> int:
        """Persists a completed task. `history` is the orchestrator's
        step/outcome list; only the `step` half of each entry is kept for
        replay purposes -- outcomes are runtime-specific (e.g. actual
        screenshot bytes/paths) and are re-derived fresh on replay rather
        than reused. `edited` records whether the user edited any
        confirmation-gate approval during this run, for the Phase 4 review
        pass -- see `flagged_for_review`."""
        steps = [entry["step"] for entry in history if "step" in entry]
        cur = self._conn.execute(
            "INSERT INTO episodes (instruction, normalized_instruction, steps_json, status, edited, "
            "created_at, schema_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                instruction, _normalize(instruction), json.dumps(steps), status, int(edited),
                time.time(), STEP_SCHEMA_VERSION,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def find_match(self, instruction: str) -> Episode | None:
        """Returns the most similar past REPLAYABLE episode, or None if
        nothing clears `_MATCH_THRESHOLD`. Only considers episodes stamped
        with the CURRENT STEP_SCHEMA_VERSION -- see module docstring for
        why: an older episode's stored steps may be missing a
        safety-relevant field a newer planner/execution fix relies on, and
        replaying it verbatim would silently resurrect the exact bug that
        fix closed."""
        normalized = _normalize(instruction)
        best: Episode | None = None
        best_score = 0.0

        placeholders = ",".join("?" for _ in _REPLAYABLE_STATUSES)
        rows = self._conn.execute(
            f"SELECT id, instruction, normalized_instruction, steps_json, status, edited, created_at "
            f"FROM episodes WHERE status IN ({placeholders}) AND schema_version = ? "
            f"ORDER BY created_at DESC",
            tuple(_REPLAYABLE_STATUSES) + (STEP_SCHEMA_VERSION,),
        ).fetchall()

        for row_id, orig_instruction, norm_instruction, steps_json, status, edited, created_at in rows:
            score = SequenceMatcher(None, normalized, norm_instruction).ratio()
            if score > best_score:
                best_score = score
                best = Episode(
                    id=row_id,
                    instruction=orig_instruction,
                    steps=json.loads(steps_json),
                    status=status,
                    created_at=created_at,
                    edited=bool(edited),
                    match_score=score,
                )

        if best is not None and best_score >= _MATCH_THRESHOLD and best.steps:
            return best
        return None

    def all_episodes(self) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT id, instruction, steps_json, status, edited, created_at FROM episodes "
            "ORDER BY created_at DESC"
        ).fetchall()
        return [
            Episode(id=r[0], instruction=r[1], steps=json.loads(r[2]), status=r[3],
                    edited=bool(r[4]), created_at=r[5])
            for r in rows
        ]

    def flagged_for_review(self) -> list[Episode]:
        """Phase 4 review pass: returns every task that either didn't finish
        cleanly (status != "done") or was completed only after the user
        edited a proposed step -- exactly the tasks the self-improvement
        loop should inspect for a correction worth remembering. See
        docs/PHASES.md Phase 4 ("Adds a review pass that flags failed/edited
        tasks for the improvement loop to inspect")."""
        rows = self._conn.execute(
            "SELECT id, instruction, steps_json, status, edited, created_at FROM episodes "
            "WHERE status != ? OR edited = 1 ORDER BY created_at DESC",
            ("done",),
        ).fetchall()
        return [
            Episode(id=r[0], instruction=r[1], steps=json.loads(r[2]), status=r[3],
                    edited=bool(r[4]), created_at=r[5])
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
