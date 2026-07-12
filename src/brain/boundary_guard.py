"""
Hard-boundary guard (fix for the gap flagged in review: the boundaries in
`context.md` / `docs/TRD.md §6` — no graded-coursework submission, no
CAPTCHA/bot-detection/signup-verification bypass, no de-safetied Brain model
swap — were previously enforced only by the LLM planner's own judgment, with
nothing in the deterministic code path actually checking for them. That
meant a prompt-injected page, a jailbroken instruction, or simply a
differently-phrased request could bypass the boundary entirely, since
nothing downstream of the planner ever re-checked its output against the
boundaries.

This module is a second, independent, deterministic layer: it runs on every
proposed step *regardless* of what the LLM planner decided, cannot be
disabled by config, and always wins over risk classification. It is
intentionally conservative (keyword/pattern based, same class of tool as
risk_classifier.py) — it is not a replacement for the LLM's own judgment,
it's a floor underneath it. A step that matches a hard-boundary pattern is
never auto-approved, never gated for possible approval, and never executed:
it's stopped and logged, and the orchestrator must halt the task.

This does NOT enforce the "de-safetied base model" boundary, since that is a
property of which model is configured (see config.py's llm_model /
planner_backend), not of individual step text — that boundary is enforced by
review process (docs/DECISIONS.md), not runtime code, and this module's
docstring says so honestly rather than pretending to check something it
can't see.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Boundary(str, Enum):
    GRADED_COURSEWORK = "graded_coursework_submission"
    CAPTCHA_BOT_DETECTION_BYPASS = "captcha_bot_detection_bypass"
    SIGNUP_VERIFICATION_BYPASS = "signup_verification_bypass"


@dataclass
class BoundaryViolation:
    boundary: Boundary
    matched_phrase: str


# Phrases indicating the step would submit graded work on the user's behalf,
# not merely view/track/summarize it (which remains allowed per context.md).
_GRADED_COURSEWORK_PHRASES = [
    "submit exam", "submit the exam", "submit quiz", "submit the quiz",
    "submit assignment", "submit the assignment", "submit answers",
    "submit my answers", "take the exam for me", "take the quiz for me",
    "complete the exam for me", "complete the quiz for me",
    "answer the exam questions", "answer the quiz questions",
    "finish the test for me", "submit the test", "turn in the assignment",
    "submit coursework", "complete the certification exam",
    "take the certification test",
]

_CAPTCHA_BYPASS_PHRASES = [
    "bypass captcha", "solve the captcha", "solve captcha", "defeat captcha",
    "get around the captcha", "bypass bot detection", "evade bot detection",
    "avoid bot detection", "bypass the verification check",
    "circumvent captcha", "captcha solving service", "anti-captcha",
    "bypass cloudflare check", "spoof the browser fingerprint",
]

_SIGNUP_VERIFICATION_BYPASS_PHRASES = [
    "bypass phone verification", "bypass email verification",
    "fake phone number for verification", "temporary email to bypass",
    "bypass age verification", "bypass identity verification",
    "create account without verifying", "skip the verification step",
    "use a burner number to verify", "bypass sms verification",
]

_BOUNDARY_TABLE = (
    (Boundary.GRADED_COURSEWORK, _GRADED_COURSEWORK_PHRASES),
    (Boundary.CAPTCHA_BOT_DETECTION_BYPASS, _CAPTCHA_BYPASS_PHRASES),
    (Boundary.SIGNUP_VERIFICATION_BYPASS, _SIGNUP_VERIFICATION_BYPASS_PHRASES),
)


def check(step: dict) -> BoundaryViolation | None:
    """Returns the first matching BoundaryViolation, or None if the step
    doesn't match any hard boundary. Checked against 'action', 'description',
    and any string values in 'params' -- an instruction embedded inside a
    params value (e.g. a typed string) is just as much a violation as one in
    the description."""
    parts = [str(step.get("action", "")), str(step.get("description", ""))]
    params = step.get("params") or {}
    if isinstance(params, dict):
        parts.extend(str(v) for v in params.values() if isinstance(v, (str, int, float)))
    text = " ".join(parts).lower()

    if not text.strip():
        return None

    for boundary, phrases in _BOUNDARY_TABLE:
        for phrase in phrases:
            if phrase in text:
                return BoundaryViolation(boundary=boundary, matched_phrase=phrase)

    return None


class BoundaryBlocked(Exception):
    """Raised by the orchestrator when a step trips a hard boundary. This is
    deliberately a hard stop (exception), not a gate denial that could be
    retried/edited/replanned around -- a hard boundary is non-negotiable per
    context.md, so there is no "edit and approve" path for it the way there
    is for a normal External/Destructive gate decision."""

    def __init__(self, violation: BoundaryViolation) -> None:
        self.violation = violation
        super().__init__(
            f"Hard boundary '{violation.boundary.value}' tripped by phrase "
            f"{violation.matched_phrase!r} — see context.md hard boundaries. "
            "Refusing to execute or gate this step."
        )
