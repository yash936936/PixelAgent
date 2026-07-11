"""
Semantic memory: durable key-value facts that persist across tasks - user
preferences (e.g. default Chrome profile) and learned UI quirks per
site/app. See docs/PHASES.md Part 3.2.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    namespace TEXT NOT NULL,
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (namespace, key)
);
"""

# Reserved namespace for general user preferences, as opposed to per-site/
# per-app quirks, which use the site/app name as their namespace (e.g.
# "github.com" -> {"cookie_banner_selector": "#accept"}).
_PREFERENCES_NAMESPACE = "_preferences"


class SemanticStore:
    """SQLite-backed key-value fact store, namespaced so preferences and
    per-site/app quirks never collide."""

    def __init__(self, db_path: str | Path = "./logs/semantic_memory.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def set_fact(self, namespace: str, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO facts (namespace, key, value_json, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(namespace, key) DO UPDATE SET value_json = excluded.value_json, "
            "updated_at = excluded.updated_at",
            (namespace, key, json.dumps(value), time.time()),
        )
        self._conn.commit()

    def get_fact(self, namespace: str, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value_json FROM facts WHERE namespace = ? AND key = ?", (namespace, key)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def all_facts(self, namespace: str) -> dict[str, Any]:
        rows = self._conn.execute(
            "SELECT key, value_json FROM facts WHERE namespace = ?", (namespace,)
        ).fetchall()
        return {key: json.loads(value_json) for key, value_json in rows}

    def delete_fact(self, namespace: str, key: str) -> None:
        self._conn.execute("DELETE FROM facts WHERE namespace = ? AND key = ?", (namespace, key))
        self._conn.commit()

    # Convenience wrappers for the reserved preferences namespace.
    def set_preference(self, key: str, value: Any) -> None:
        self.set_fact(_PREFERENCES_NAMESPACE, key, value)

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.get_fact(_PREFERENCES_NAMESPACE, key, default)

    def close(self) -> None:
        self._conn.close()
