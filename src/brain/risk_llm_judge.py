"""
LLM-based risk-judge fallback for ambiguous steps (fix for the gap flagged
in review: risk_classifier.py's docstring long promised an "LLM judgment
fallback for ambiguous cases... wired in orchestrator.py," but no such
wiring ever existed anywhere in the codebase — every step's risk was decided
by keyword matching alone, with no second opinion for text that matched no
keyword at all.

This module provides that second opinion. It is deliberately narrow in
scope: it is only ever consulted when RiskClassifier.classify_with_confidence()
returns confident=False (i.e. no keyword matched, defaulting to Local) --
see orchestrator.py's wiring. It can only ever escalate a step from Local to
External/Destructive, never downgrade a keyword-matched result -- so a
misbehaving or manipulated LLM response here can make the system more
cautious, never less. If the LLM call itself fails for any reason (network,
parsing, quota), this fails safe by returning the keyword-based result
unchanged rather than blocking the whole task on an availability issue.
"""
from __future__ import annotations

import json
from typing import Callable

from src.brain.risk_classifier import Risk

_JUDGE_PROMPT = """You are a safety classifier for a desktop automation \
agent. You will be given a single proposed action that a keyword-based \
filter found no concerning keywords in (so it defaulted to "local/reversible \
only"). Your ONLY job is to say whether that default is actually wrong \
because the KEYWORD FILTER MISSED something -- for example, evasive \
phrasing of a destructive or externally-visible action.

Classify the action into exactly one of: "local", "external", "destructive".
- local: only affects local UI state, fully reversible, doesn't affect anything outside this session
- external: visible to other people/systems, or hard to undo (e.g. sending something, posting, purchasing)
- destructive: deletes or overwrites the user's data

Respond with ONLY a JSON object: {"risk": "local" | "external" | "destructive", "reason": "one short sentence"}
"""


def build_llm_risk_judge(generate_fn: Callable[[str, str], str]) -> Callable[[dict], Risk | None]:
    """generate_fn(system_prompt, user_content) -> raw text, same shape as
    LocalPlanner's injected callable in planner.py, so main.py can reuse
    whatever LLM transport it already built for planning (hosted Gemini or
    a local endpoint) without a second client. Returns a callable
    judge(step) -> Risk | None; None means "judge couldn't produce a usable
    answer, keep the keyword-based default" rather than raising, so a
    transient LLM failure degrades to Phase-1-era behavior instead of
    crashing the task."""

    def judge(step: dict) -> Risk | None:
        user_content = json.dumps(
            {
                "action": step.get("action"),
                "description": step.get("description"),
                "params": step.get("params", {}),
            }
        )
        try:
            raw_text = generate_fn(_JUDGE_PROMPT, user_content).strip()
            parsed = json.loads(raw_text)
            risk_str = str(parsed.get("risk", "")).strip().lower()
            return {
                "local": Risk.LOCAL,
                "external": Risk.EXTERNAL,
                "destructive": Risk.DESTRUCTIVE,
            }.get(risk_str)
        except Exception:  # noqa: BLE001 - fail safe to "no opinion", never crash the task
            return None

    return judge
