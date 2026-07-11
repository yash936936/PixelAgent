"""
Turns the natural-language instruction (+ current page/screen state) into the
NEXT SINGLE step, not a full up-front plan — so the Brain can react to actual
state rather than committing to a stale plan. See docs/CODE_LOGIC.md §4 for the
PlannerBackend interface this follows (Phase 4 will add a local-model backend
behind the same interface).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

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


class PlannerBackend(ABC):
    """Interface every planner implementation follows, so the Brain never
    depends on a specific backend. See docs/CODE_LOGIC.md §4."""

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
        raw_text = (response.text or "").strip()

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
