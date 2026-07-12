"""
Turns the natural-language instruction (+ current page/screen state) into the
NEXT SINGLE step, not a full up-front plan — so the Brain can react to actual
state rather than committing to a stale plan. See docs/CODE_LOGIC.md §4 for the
PlannerBackend interface this follows (Phase 4 will add a local-model backend
behind the same interface).

Fix for a gap flagged in review: LoopAudit.est_cost (observability/logger.py)
was tracked as a real field but nothing anywhere ever computed a real cost --
every call site passed the default 0.0, so "estimated cost per task" was
always zero regardless of how many LLM calls a task made. HostedLLMPlanner
now reads real input/output token counts off the Gemini response's
usage_metadata and estimates a dollar cost from them, exposed via
`last_call_cost`/`last_call_tokens` so orchestrator.py can pass a real
number to logger.log_step() instead of the previous always-0.0 default.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Callable

from google import genai
from google.genai import types

SYSTEM_PROMPT = """You are the planning module of Pixel, a Windows desktop \
automation agent. Given a user's task instruction, the current browser/page \
state, and the history of steps already taken, output the SINGLE next step \
needed to make progress — not the whole plan.

Respond with ONLY a JSON object, no other text, matching this schema:
{
  "action": "navigate" | "click" | "type" | "scroll" | "screenshot" | "done",
  "description": "short human-readable description of what this step does and why",
  "target_type": "web" | "desktop",
  "params": { ... action-specific parameters, e.g. {"url": "..."} or {"selector": "...", "text": "..."} }
}

If the task is already complete, respond with {"action": "done", "description": "...", "target_type": "web", "params": {}}.
Never invent a step that isn't necessary for the instruction. Keep each step minimal and concrete."""

# Approximate per-1M-token USD pricing used only for observability/cost
# estimation (docs/TRD.md §3.1's max-step budget is about step count, this
# is a supplementary signal, not a billing-accurate figure). Deliberately
# conservative/rough -- update here if Gemini pricing changes, in one place
# rather than scattered per call site.
_COST_PER_1M_INPUT_TOKENS_USD = 0.075
_COST_PER_1M_OUTPUT_TOKENS_USD = 0.30


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1_000_000 * _COST_PER_1M_INPUT_TOKENS_USD
        + output_tokens / 1_000_000 * _COST_PER_1M_OUTPUT_TOKENS_USD
    )


class PlannerBackend(ABC):
    """Interface every planner implementation follows, so the Brain never
    depends on a specific backend. See docs/CODE_LOGIC.md §4."""

    #: Real cost of the most recent next_step() call, in USD, or 0.0 if
    #: unknown/not applicable (e.g. LocalPlanner has no meaningful notion of
    #: dollar cost, so it stays 0.0 rather than fabricating a number).
    last_call_cost: float = 0.0

    @abstractmethod
    def next_step(
        self, instruction: str, screen_state: dict[str, Any], history: list[dict]
    ) -> dict[str, Any]:
        ...


class HostedLLMPlanner(PlannerBackend):
    """Default for Phases 1-3: calls the hosted Gemini API (free-tier eligible
    via https://aistudio.google.com/apikey — see docs/DECISIONS.md for the
    Anthropic -> Gemini swap decision and its rationale). Uses the current
    `google-genai` SDK, not the deprecated `google-generativeai` package."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self.last_call_cost: float = 0.0

    def _generate_fn(self, system_prompt: str, user_content: str) -> str:
        """Exposes the raw (system_prompt, user_content) -> text transport
        this planner already wraps, in the same shape LocalPlanner's
        injected generate_fn takes. This is what lets main.py build an LLM
        risk-judge fallback (risk_llm_judge.py) that works identically
        regardless of which PlannerBackend is configured, without a second
        LLM client (fix for the gap flagged in review: the LLM risk-judge
        fallback never existed in the first place, partly because there
        was no reusable raw-generate transport to build it on)."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )
        return (response.text or "").strip()

    def next_step(
        self, instruction: str, screen_state: dict[str, Any], history: list[dict]
    ) -> dict[str, Any]:
        user_content = json.dumps(
            {
                "instruction": instruction,
                "current_state": screen_state,
                "steps_so_far": history,
            }
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        self.last_call_cost = self._estimate_cost_from_response(response)
        raw_text = (response.text or "").strip()
        return _parse_step(raw_text)

    def _estimate_cost_from_response(self, response) -> float:
        """Reads real token counts off the Gemini response when available;
        falls back to 0.0 (not a guess) if usage_metadata is missing, since
        an approximate character-count guess presented as a "cost" would be
        more misleading than an honest zero. This directly fixes the gap
        where est_cost was unconditionally 0.0 for every task regardless of
        real usage."""
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return 0.0
        input_tokens = getattr(usage, "prompt_token_count", None) or 0
        output_tokens = getattr(usage, "candidates_token_count", None) or 0
        return estimate_cost_usd(input_tokens, output_tokens)


class LocalFineTunedPlanner(PlannerBackend):
    """Track B (per docs/DECISIONS.md's 2026-07-12 model-training entry):
    a locally-hosted, LoRA-fine-tuned open-weights model swapped in behind
    the same PlannerBackend interface as HostedLLMPlanner -- so
    orchestrator.py, risk_classifier.py, boundary_guard.py, and gate.py need
    ZERO changes regardless of which backend is configured. This is the
    class docs/CODE_LOGIC.md §4 named `LocalFineTunedPlanner` from the
    start ("Phase 4 optional swap-in, trained per OpenManus-style pipeline,
    same interface").

    This class only ever changes where the *proposed next step* comes
    from -- it never changes whether that step gets risk-classified and
    gated. A bug or a bad fine-tune here can make Pixel propose a worse
    step, but structurally cannot make it skip risk_classifier.py's or
    boundary_guard.py's checks, since those run in orchestrator.py
    regardless of planner backend. This is the deliberate design boundary
    from TRD.md §6: the planner is allowed to be experimental, the safety
    layer underneath it is not.

    `generate_fn(system_prompt, user_content) -> str` is injected so this
    class has no hard dependency on any specific local-serving stack (e.g.
    a raw HTTP call to a vLLM/text-generation-inference server hosting the
    fine-tuned LoRA adapter) -- callers wire up the actual transport in
    src/main.py based on config.py's `local_planner_endpoint`. See
    training/README.md for how the underlying model is actually trained,
    and training/model_card_template.md for the auditability record TRD.md
    §6 requires before this class is ever pointed at a new base model.
    """

    def __init__(self, generate_fn: Callable[[str, str], str]) -> None:
        self._generate_fn = generate_fn
        self.last_call_cost: float = 0.0  # local inference: no per-call $ cost to track

    def next_step(
        self, instruction: str, screen_state: dict[str, Any], history: list[dict]
    ) -> dict[str, Any]:
        user_content = json.dumps(
            {
                "instruction": instruction,
                "current_state": screen_state,
                "steps_so_far": history,
            }
        )
        raw_text = self._generate_fn(SYSTEM_PROMPT, user_content).strip()
        return _parse_step(raw_text)


# Backward-compat alias: this class was previously named LocalPlanner. Kept
# so any existing import (including main.py before this rename, and any
# external code) keeps working without modification.
LocalPlanner = LocalFineTunedPlanner


def _parse_step(raw_text: str) -> dict[str, Any]:
    """Shared response parsing/validation for every PlannerBackend
    implementation, so HostedLLMPlanner and LocalFineTunedPlanner can never
    drift on what counts as a valid step."""
    try:
        step = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Planner returned non-JSON output, cannot proceed safely: {raw_text!r}"
        ) from exc

    for required in ("action", "description", "target_type", "params"):
        if required not in step:
            raise ValueError(f"Planner step missing required field '{required}': {step}")

    return step


def build_http_generate_fn(endpoint: str) -> Callable[[str, str], str]:
    """Convenience helper for wiring LocalPlanner to a plain HTTP JSON
    endpoint (e.g. an Ollama-style `/api/generate` route) without adding a
    new third-party HTTP dependency -- uses the stdlib `urllib` only. The
    endpoint is expected to accept {"system": ..., "prompt": ...} and return
    JSON with a top-level "response" string field; adapt this helper if
    your local server uses a different contract."""
    import urllib.request

    def _generate(system_prompt: str, user_content: str) -> str:
        payload = json.dumps({"system": system_prompt, "prompt": user_content}).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["response"]

    return _generate
