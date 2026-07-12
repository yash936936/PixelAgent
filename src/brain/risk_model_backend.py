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

from src.brain.risk_classifier import Risk


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
