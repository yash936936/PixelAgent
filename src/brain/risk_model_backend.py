"""
Track B (per docs/DECISIONS.md's 2026-07-12 model-training entry): a
SEPARATE trained-model interface for risk/boundary judgment, deliberately
not sharing a class hierarchy with PlannerBackend (planner.py) even though
the shapes look similar. This is intentional, not an oversight -- the two
models have different trust levels and different failure semantics:

- PlannerBackend errors make Pixel propose a worse step. Downstream
  risk_classifier.py + boundary_guard.py + the gate still catch anything
  External/Destructive/boundary-violating regardless.
- RiskModelBackend errors, if this model were ever trusted alone, could let
  something dangerous slip to auto-execution. That is why this module's
  contract is additive-only: a RiskModelBackend can escalate a step's
  classification (Local -> External/Destructive), but nothing in this
  codebase ever lets it downgrade one, and it never overrides
  boundary_guard.py's hard-boundary block. See orchestrator.py's
  `_classify_risk()` for exactly how this is enforced structurally, not
  just by convention.

Any RiskModelBackend implementation -- hosted (risk_llm_judge.py's
build_llm_risk_judge, wrapped below as HostedRiskJudge) or a locally
fine-tuned LoRA model (LocalFineTunedRiskModel) -- must pass the adversarial
eval harness in eval/adversarial_boundary_eval.py above the documented
recall threshold BEFORE it is wired into orchestrator.py's llm_risk_judge
parameter. See eval/README.md.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Callable

from src.brain.risk_classifier import _READ_ONLY_GUARDS, Risk
from src.brain.semantic_matcher import SemanticMatcher

_ACTION_VERBS = ("click", "press", "tap", "hit", "select")


def _is_read_only_framed(text: str, description_text: str) -> bool:
    """Mirrors risk_classifier.classify_with_confidence()'s own read-only
    guard, reused here so the semantic judge doesn't escalate exactly the
    phrasing the keyword classifier already knows to treat as inspection
    rather than action (e.g. "check if the delete button exists"). Without
    this, the semantic matcher's whole-phrase similarity happily scores
    "check if X exists" against boundary/destructive exemplars on shared
    generic n-grams ("check", "the", "page") even though nothing is
    actually being done -- see the benign_but_tricky eval category this is
    meant to protect.

    Unlike risk_classifier._has_actual_verb(), this has no single keyword
    to anchor the "verb immediately before X" check on (the semantic
    matcher scores the whole phrase, not a specific keyword match), so it
    uses a simpler, still-conservative rule: any real action verb anywhere
    in the description overrides the guard (e.g. "check if delete works,
    then click delete" still escalates). This is intentionally slightly
    more permissive than risk_classifier's positional check -- that's fine
    here because being wrong in this direction means "falls back to no
    opinion, keyword result stands," never "silently escalates.\""""
    lowered = text.lower()
    is_guarded = any(guard in lowered for guard in _READ_ONLY_GUARDS)
    if not is_guarded:
        return False
    return not any(verb in description_text for verb in _ACTION_VERBS)


class RiskModelBackend(ABC):
    """Interface every trained/hosted risk-judgment model follows. Never
    inherits from or is substitutable for PlannerBackend -- see this
    module's docstring for why that separation is deliberate."""

    #: Real cost of the most recent judge() call, in USD, or 0.0 if
    #: unknown/not applicable (mirrors PlannerBackend.last_call_cost).
    last_call_cost: float = 0.0

    @abstractmethod
    def judge(self, step: dict) -> Risk | None:
        """Returns a Risk if the model has an opinion, or None if it
        couldn't produce a usable answer (fails safe: caller keeps
        whatever the keyword-based RiskClassifier decided)."""
        ...


_JUDGE_SYSTEM_PROMPT = """You are a safety classifier for a desktop automation \
agent. You will be given a single proposed action. Classify it into exactly \
one of: "local", "external", "destructive".
- local: only affects local UI state, fully reversible, doesn't affect anything outside this session
- external: visible to other people/systems, or hard to undo (e.g. sending something, posting, purchasing)
- destructive: deletes or overwrites the user's data

Respond with ONLY a JSON object: {"risk": "local" | "external" | "destructive", "reason": "one short sentence"}
"""


class HostedRiskJudge(RiskModelBackend):
    """Wraps risk_llm_judge.py's existing hosted-LLM judge behind the
    RiskModelBackend interface, so orchestrator.py and the eval harness can
    treat a hosted judge and a locally fine-tuned one identically."""

    def __init__(self, generate_fn: Callable[[str, str], str]) -> None:
        self._generate_fn = generate_fn
        self.last_call_cost: float = 0.0

    def judge(self, step: dict) -> Risk | None:
        user_content = json.dumps(
            {
                "action": step.get("action"),
                "description": step.get("description"),
                "params": step.get("params", {}),
            }
        )
        try:
            raw_text = self._generate_fn(_JUDGE_SYSTEM_PROMPT, user_content).strip()
            parsed = json.loads(raw_text)
            risk_str = str(parsed.get("risk", "")).strip().lower()
            return {
                "local": Risk.LOCAL,
                "external": Risk.EXTERNAL,
                "destructive": Risk.DESTRUCTIVE,
            }.get(risk_str)
        except Exception:  # noqa: BLE001 - fail safe to "no opinion"
            return None


# Exemplar phrases for SemanticRiskJudge below. Deliberately independent
# paraphrases, NOT copied from eval/adversarial_cases.jsonl -- see
# semantic_matcher.py's module docstring for why that separation matters
# (using the eval set's own phrasing as training/exemplar data would let
# this module cheat the eval it's meant to be honestly scored against).
_DESTRUCTIVE_EXEMPLARS = [
    "make this go away for good",
    "get rid of this permanently",
    "make sure this can never be recovered",
    "erase this completely",
    "wipe this so nothing is left",
    "make it like this never existed",
    "clear this out entirely and don't keep a copy",
    "take this off the system for good",
    "destroy this data",
    "undo this account so it no longer exists",
    "shut this down and remove it from existence",
    "start over by clearing everything here",
]

_EXTERNAL_EXEMPLARS = [
    "let other people see this",
    "share this outside of just me",
    "make this visible to everyone",
    "send this off to someone else",
    "hand this over to another person",
    "put this out publicly",
    "finalize the transaction",
    "go ahead and complete the purchase",
    "let the rest of the team know about this",
    "give someone else access to this",
    "commit to this and make it official",
    "notify other people about this",
]

_CAPTCHA_BYPASS_EXEMPLARS = [
    "solve the little puzzle so the site lets us through",
    "get past the human-check the page put up",
    "trick the site into thinking a person did this",
    "handle the verification puzzle for me",
    "beat the anti-bot check on this page",
]

_SIGNUP_VERIFICATION_BYPASS_EXEMPLARS = [
    "use a fake number so the site accepts it as verified",
    "get past the identity check without proving who I am",
    "skip proving it's really me on this signup",
    "trick the verification step into passing",
    "make the site think I confirmed my phone when I didn't",
]

_GRADED_COURSEWORK_EXEMPLARS = [
    "answer the rest of these questions for me and submit it",
    "finish this test on my behalf and turn it in",
    "pick whatever answers make sense and hand in the assignment",
    "complete this graded quiz for me",
    "submit this exam using your own answers",
]

_BOUNDARY_EXEMPLAR_BANK = {
    "captcha_bot_detection_bypass": _CAPTCHA_BYPASS_EXEMPLARS,
    "signup_verification_bypass": _SIGNUP_VERIFICATION_BYPASS_EXEMPLARS,
    "graded_coursework_submission": _GRADED_COURSEWORK_EXEMPLARS,
}


class SemanticRiskJudge(RiskModelBackend):
    """Zero-cost, zero-dependency intermediate between the keyword-only
    baseline and Track B's eventual trained LoRA model. Scores a step's
    description against small hand-written exemplar banks for
    destructive/external intent using character-n-gram cosine similarity
    (semantic_matcher.py) instead of literal substring matching -- this is
    what lets it catch paraphrases the keyword tables miss by construction.

    Deliberately conservative: only returns an opinion when the best match
    clears `threshold`, and returns None (no opinion, caller keeps the
    keyword result) otherwise -- same fail-safe contract as HostedRiskJudge
    and LocalFineTunedRiskModel. This does NOT replace either of those; it
    is meant to be tried FIRST (it's free and instant), with the LLM judge
    still available as a fallback for whatever this also misses.

    This does not need or use the eval-gate deployment process described
    in eval/README.md/docs/TRD.md §6.1 -- that gate exists specifically for
    the LoRA-trained backend where wrong-but-confident behavior is opaque
    and hard to audit. This class's exemplar list is plain, readable text
    any reviewer can inspect directly, same as the keyword tables it
    augments -- but it should still be run through
    eval/adversarial_boundary_eval.py before being trusted, exactly like
    any other judge, since "inspectable" isn't the same as "correct."
    """

    #: Below this cosine-similarity score, treat the match as noise rather
    #: than a real signal. Chosen conservatively (favoring "no opinion"
    #: over a confident-looking wrong answer) -- tune against
    #: eval/adversarial_boundary_eval.py's benign_but_tricky category if
    #: this ever needs adjusting.
    threshold: float = 0.35

    def __init__(self, threshold: float = 0.35) -> None:
        self.threshold = threshold
        self.last_call_cost: float = 0.0
        self._matcher = SemanticMatcher(
            exemplars={
                "destructive": _DESTRUCTIVE_EXEMPLARS,
                "external": _EXTERNAL_EXEMPLARS,
            }
        )

    def judge(self, step: dict) -> Risk | None:
        action = str(step.get("action", ""))
        description = str(step.get("description", ""))
        text = f"{action} {description}".strip()
        if not text:
            return None
        if _is_read_only_framed(text, description.lower()):
            return None

        result = self._matcher.best_match(text)
        if result.label is None or result.score < self.threshold:
            return None

        return Risk.DESTRUCTIVE if result.label == "destructive" else Risk.EXTERNAL


def semantic_boundary_match(step: dict, threshold: float = 0.4):
    """Additive semantic pass for the hard-boundary categories
    (boundary_guard.py's Boundary enum), using the same character-n-gram
    approach as SemanticRiskJudge above. Returns a (boundary_value, score,
    matched_exemplar) tuple or None -- deliberately returns a plain tuple
    rather than a BoundaryViolation so boundary_guard.py (which has no
    dependency on this module by default) stays importable/testable with
    zero new dependencies for anyone who doesn't opt into this layer.

    Kept as a separate, higher-threshold, opt-in function rather than
    merged into boundary_guard.check() itself: a hard boundary is
    non-negotiable and stops the task outright with no gate/edit path, so
    a false positive here is much more disruptive than a false positive on
    an ordinary External/Destructive risk tier. Callers (e.g.
    orchestrator.py) should treat this as a second, best-effort check
    layered on top of boundary_guard.check() -- never as a replacement for
    it, and should log both the keyword and semantic verdicts so a
    reviewer can see which layer caught what.
    """
    text = f"{step.get('action', '')} {step.get('description', '')}".strip()
    if not text:
        return None
    description = str(step.get("description", ""))
    if _is_read_only_framed(text, description.lower()):
        return None

    matcher = SemanticMatcher(exemplars=_BOUNDARY_EXEMPLAR_BANK)
    result = matcher.best_match(text)
    if result.label is None or result.score < threshold:
        return None

    return (result.label, result.score, result.matched_exemplar)


class LocalFineTunedRiskModel(RiskModelBackend):
    """Track B's second (separate) trained model: a small open-weights
    instruct model + LoRA adapter, fine-tuned specifically on risk/boundary
    judgment examples (see training/README.md's "risk model" track --
    distinct from the planner's training run and, critically, trained on a
    different, adversarially-focused dataset: eval/adversarial_cases.jsonl
    plus any real corrections harvested from trace logs via
    trace_replay.py's unclassified_or_missing_risk()).

    Deployment gate (non-negotiable, see docs/TRD.md §6 and
    docs/DECISIONS.md): this class MUST NOT be wired into
    orchestrator.py's `llm_risk_judge` parameter until
    eval/adversarial_boundary_eval.py reports a recall >= the threshold
    documented in eval/README.md on the held-out adversarial set. There is
    no code-level enforcement of that gate (it can't be, since gating a
    deployment decision isn't something runtime code can check about
    itself) -- it is a process requirement, stated here as plainly as
    boundary_guard.py states the equivalent limit on itself.

    `generate_fn(system_prompt, user_content) -> str` is injected exactly
    like LocalFineTunedPlanner, wired in src/main.py from
    config.py's `local_risk_model_endpoint` -- deliberately a SEPARATE
    config value and a SEPARATE local model server/adapter from the
    planner's, even if both happen to run on the same machine, so the two
    models can be evaluated, versioned, and rolled back independently.
    """

    def __init__(self, generate_fn: Callable[[str, str], str]) -> None:
        self._generate_fn = generate_fn
        self.last_call_cost: float = 0.0

    def judge(self, step: dict) -> Risk | None:
        user_content = json.dumps(
            {
                "action": step.get("action"),
                "description": step.get("description"),
                "params": step.get("params", {}),
            }
        )
        try:
            raw_text = self._generate_fn(_JUDGE_SYSTEM_PROMPT, user_content).strip()
            parsed = json.loads(raw_text)
            risk_str = str(parsed.get("risk", "")).strip().lower()
            return {
                "local": Risk.LOCAL,
                "external": Risk.EXTERNAL,
                "destructive": Risk.DESTRUCTIVE,
            }.get(risk_str)
        except Exception:  # noqa: BLE001 - fail safe to "no opinion"
            return None
