"""
Classifies a proposed step into Local / External / Destructive risk, per
docs/TRD.md §5. Rule-based keyword matching first; LLM judgment fallback for
ambiguous cases (wired in orchestrator.py, not here, to keep this module
dependency-free and unit-testable).

Phase 5 hardening (docs/PHASES.md Phase 5): the keyword tables below were
expanded from the categories of misses/edits observed across the Phase 1-4
logged usage patterns (per-category rationale in docs/DECISIONS.md). Also
adds an explicit "negation guard" so a step whose text only *mentions* a
sensitive word inside an unmistakably safe/read-only framing (e.g. "check
whether the delete button exists") isn't overclassified, without weakening
the fail-safe default for genuinely ambiguous text.
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
    # Phase 5 additions — file/data destruction phrasing seen in logs:
    "format drive", "format disk", "empty trash", "empty recycle bin",
    "clear history", "clear browsing data", "factory reset", "reset settings",
    "revoke access", "revoke token", "delete account", "deactivate account",
    "cancel subscription", "unsubscribe", "truncate table", "drop database",
    "rm -rf", "shred", "permanently delete", "empty the bin",
    # Destructive git/repo operations beyond force-push:
    "delete branch", "delete repo", "delete repository", "hard reset",
]

_EXTERNAL_KEYWORDS = [
    "send", "email", "submit", "star", "fork", "post", "publish", "purchase",
    "buy", "checkout", "pay", "comment", "reply", "tweet", "share", "upload",
    "commit", "push", "merge", "sign up", "signup", "register", "subscribe",
    "follow", "like", "vote", "apply",
    # Phase 5 additions — external/irreversible actions seen in real usage
    # logs that weren't covered by the Phase 1 table:
    "message", "dm", "direct message", "invite", "accept invite",
    "create issue", "open pull request", "open issue", "approve pull request",
    "request review", "assign", "grant access", "add collaborator",
    "book", "reserve", "reservation", "schedule meeting", "send invoice",
    "transfer", "wire", "donate", "tip", "endorse", "leave a rating",
    "submit review", "write a review",
    "confirm order", "place order", "add to cart and checkout",
    "connect account", "link account", "authorize app", "install extension",
    "enable notifications", "opt in", "opt-in", "accept terms",
    "friend request", "connection request",
]

# Phrasing that, when present, indicates the step is only inspecting or
# describing state rather than performing the action — used to avoid
# overclassifying read-only steps that merely mention a sensitive verb.
# This NEVER downgrades a step below Local's neighbors silently; it only
# prevents a false-positive escalation when one of these guard phrases is
# present alongside the keyword, and any doubt still fails safe (see
# classify()'s empty-text handling below, which is unchanged).
_READ_ONLY_GUARDS = [
    "check whether", "check if", "look for", "find the", "locate the",
    "is there a", "does the page have", "hover over", "read the",
    "take a screenshot of", "screenshot", "verify that", "confirm that the",
]


class RiskClassifier:
    def classify(self, step: dict) -> Risk:
        """step is expected to have at least 'action' and optionally
        'description' string fields describing what the step will do."""
        risk, _confident = self.classify_with_confidence(step)
        return risk

    def classify_with_confidence(self, step: dict) -> tuple[Risk, bool]:
        """Like classify(), but also reports whether a keyword actually
        matched (True) versus the result being the unmatched default of
        Local (False -- "confident" here means "confident there's nothing
        concerning," which is exactly the case that's cheapest to get wrong
        silently). This is what fixes the gap where classify() always
        returned a definite-looking answer even for text that matched
        nothing -- callers (see orchestrator.py) can now route the
        low-confidence case to an LLM judge instead of trusting an
        unmatched default at face value."""
        text = f"{step.get('action', '')} {step.get('description', '')}".lower()
        description_text = str(step.get("description", "")).lower()

        if not text.strip():
            return Risk.EXTERNAL, True

        is_read_only_framed = any(guard in text for guard in _READ_ONLY_GUARDS)

        for kw in _DESTRUCTIVE_KEYWORDS:
            if kw in text:
                if is_read_only_framed and not _has_actual_verb(description_text, kw):
                    continue
                return Risk.DESTRUCTIVE, True

        for kw in _EXTERNAL_KEYWORDS:
            if kw in text:
                if is_read_only_framed and not _has_actual_verb(description_text, kw):
                    continue
                return Risk.EXTERNAL, True

        return Risk.LOCAL, False

    def needs_confirmation(self, risk: Risk) -> bool:
        return risk in (Risk.EXTERNAL, Risk.DESTRUCTIVE)


def _has_actual_verb(text: str, keyword: str) -> bool:
    """Very conservative check: if the keyword is immediately preceded by an
    imperative-style action verb ("click", "press", "tap", "hit") WITHIN THE
    DESCRIPTION TEXT ONLY, treat it as a real action even inside a
    read-only-guarded sentence, so phrasing like "check if the delete
    button works, then click delete" still escalates correctly.

    Fix for a bug the adversarial eval harness caught on day one
    (eval/adversarial_boundary_eval.py, case adv_016): this used to be
    checked against the combined "{action} {description}" text, and every
    step's `action` field (e.g. "click") is itself one of these verbs --
    so a step routed as action="click" always satisfied this check
    regardless of what its description actually said, silently defeating
    the read-only guard for the single most common action type. Now takes
    only the description text, so the routing action field can never
    substitute for an actual verb appearing in the step's own description.

    Defaults to True (i.e. still classify as risky) whenever this can't
    confidently tell -- the guard only suppresses false positives it is
    sure about."""
    action_verbs = ("click", "press", "tap", "hit", "select")

    start = 0
    found_any = False
    while True:
        idx = text.find(keyword, start)
        if idx == -1:
            break
        found_any = True
        prefix = text[:idx]
        if any(verb in prefix for verb in action_verbs):
            return True
        start = idx + 1

    # No occurrence of the keyword had a preceding verb in the description.
    # If the keyword never appeared at all (shouldn't happen given the
    # caller already matched it against the combined text, but stay safe),
    # default to True rather than silently suppressing.
    return not found_any
