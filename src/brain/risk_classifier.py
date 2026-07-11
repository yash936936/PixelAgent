"""
Classifies a proposed step into Local / External / Destructive risk, per
docs/TRD.md §5. Rule-based keyword matching first; LLM judgment fallback for
ambiguous cases (wired in orchestrator.py, not here, to keep this module
dependency-free and unit-testable).
"""
from __future__ import annotations

from enum import Enum


class Risk(str, Enum):
    LOCAL = "local"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


# Keyword -> risk. Checked against the step's "action" and "description" fields.
# Destructive is checked first (most severe), then External, else Local.
_DESTRUCTIVE_KEYWORDS = [
    "delete", "remove", "force push", "force-push", "overwrite", "drop table",
    "uninstall", "wipe", "erase", "close issue", "close pull request",
]

_EXTERNAL_KEYWORDS = [
    "send", "email", "submit", "star", "fork", "post", "publish", "purchase",
    "buy", "checkout", "pay", "comment", "reply", "tweet", "share", "upload",
    "commit", "push", "merge", "sign up", "signup", "register", "subscribe",
    "follow", "like", "vote", "apply",
]


class RiskClassifier:
    def classify(self, step: dict) -> Risk:
        """step is expected to have at least 'action' and optionally
        'description' string fields describing what the step will do."""
        text = f"{step.get('action', '')} {step.get('description', '')}".lower()

        if not text.strip():
            # No information to classify on — fail safe to the most cautious
            # class rather than silently defaulting to Local. See docs/DEBUG.md
            # "Special checks by subsystem" for why this must never happen.
            return Risk.EXTERNAL

        for kw in _DESTRUCTIVE_KEYWORDS:
            if kw in text:
                return Risk.DESTRUCTIVE

        for kw in _EXTERNAL_KEYWORDS:
            if kw in text:
                return Risk.EXTERNAL

        return Risk.LOCAL

    def needs_confirmation(self, risk: Risk) -> bool:
        return risk in (Risk.EXTERNAL, Risk.DESTRUCTIVE)
