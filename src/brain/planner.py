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

import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# Real bug found live on 2026-08-01 (docs/DECISIONS.md): a 429
# RESOURCE_EXHAUSTED rate-limit error from the Gemini API crashed the whole
# task with an unhandled traceback -- the 2026-08-01 retry fix only catches
# ValueError from _parse_step (malformed/truncated JSON), which is a
# completely different failure mode from an API-level error raised by the
# google-genai SDK itself (google.genai.errors.ClientError). A rate limit
# is transient and the API even tells us how long to wait
# (RetryInfo.retryDelay in the error body) -- this deserves an actual
# backoff-and-retry, not a crash.
_RATE_LIMIT_MAX_ATTEMPTS = 2
_RATE_LIMIT_DEFAULT_BACKOFF_SECONDS = 15.0
#: Caps whatever the server's own RetryInfo suggests -- found live that the
#: free tier can suggest a full ~30s+ per attempt, which compounds badly
#: across a multi-step task. None disables the cap (trust the server as-is).
_RATE_LIMIT_MAX_BACKOFF_SECONDS: float | None = 20.0


def _extract_retry_delay_seconds(exc: genai_errors.APIError) -> float:
    """Reads the API's own suggested wait time
    (google.rpc.RetryInfo.retryDelay, e.g. "30s") out of the error body
    when present, falling back to a fixed default otherwise. Trusting the
    server's own suggestion is more accurate than guessing a fixed backoff,
    and avoids retrying sooner than the server is willing to accept another
    request."""
    try:
        error_details = (exc.details or {}).get("error", {}).get("details", [])
        for detail in error_details:
            if str(detail.get("@type", "")).endswith("RetryInfo"):
                delay_str = str(detail.get("retryDelay", ""))
                if delay_str.endswith("s"):
                    return float(delay_str[:-1])
    except Exception:  # noqa: BLE001 - fall through to the default below
        pass
    return _RATE_LIMIT_DEFAULT_BACKOFF_SECONDS

SYSTEM_PROMPT = """You are the planning module of Pixel, a Windows desktop \
automation agent. Given a user's task instruction, the current browser/page \
state, and the history of steps already taken, output the SINGLE next step \
needed to make progress — not the whole plan.

Respond with ONLY a JSON object, no other text, matching this schema:
{
  "action": "navigate" | "click" | "double_click" | "type" | "scroll" | "screenshot" | "hotkey" | "done",
  "description": "short human-readable description of what this step does and why",
  "target_type": "web" | "desktop",
  "params": { ... action-specific parameters, schema depends on target_type -- see below }
}

IMPORTANT: "params" has a DIFFERENT shape depending on "target_type". Getting this wrong makes
the step fail to execute even though it looked reasonable, so follow this exactly:

- target_type "web" (a browser page, e.g. Playwright): click/type use {"selector": "..."} (a CSS
  selector or accessible role/text Playwright can resolve), e.g. {"selector": "text=Submit"}.
- target_type "desktop" (a native OS window/app with no DOM, e.g. the Start menu, Notepad, a
  Windows dialog): click/double_click do NOT use "selector" at all -- there is no DOM to select
  against. Use EITHER {"target_text": "..."} (a short, visible on-screen text/label the perception
  layer will locate via OCR, e.g. {"target_text": "Start"}) OR explicit {"x": <int>, "y": <int>}
  screen coordinates if you already know them from a prior screenshot. Desktop "type" steps use
  {"text": "..."} (types at the current focus, no target needed) and SHOULD also include
  {"expect_window_contains": "..."} whenever the text is meant to go into a specific app/window
  (e.g. after opening Notepad, use {"text": "...", "expect_window_contains": "Notepad"}) -- this is
  verified for real before typing and prevents text landing in the wrong window if the target app is
  still launching. Omit expect_window_contains only when typing into whatever already has focus is
  actually intended (e.g. typing into a search box you just clicked into). Never put "selector" in a
  target_type="desktop" step's params.
- target_type "desktop" "hotkey" action: {"keys": ["win"]} presses a real keyboard shortcut directly
  -- no OCR or coordinates involved at all, so it can never miss a click target. STRONGLY PREFER this
  over clicking for opening the Start menu: use
  {"action": "hotkey", "target_type": "desktop", "params": {"keys": ["win"]}} rather than
  {"action": "click", "target_type": "desktop", "params": {"target_text": "Start"}}. Live runs have
  repeatedly needed a mid-task replan to recover from an unreliable OCR click on the Start button
  (small taskbar icon, easy to miss) -- pressing the physical Windows key always opens the Start menu
  regardless of taskbar layout, icon rendering, or screen resolution, and needs no perception step at
  all. Other useful hotkeys: {"keys": ["enter"]}, {"keys": ["esc"]}, {"keys": ["alt", "tab"]},
  {"keys": ["ctrl", "a"]}.

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

    def __init__(
        self,
        api_key: str,
        model: str,
        rate_limit_max_attempts: int = _RATE_LIMIT_MAX_ATTEMPTS,
        rate_limit_max_backoff_seconds: float | None = _RATE_LIMIT_MAX_BACKOFF_SECONDS,
    ) -> None:
        """rate_limit_max_attempts/rate_limit_max_backoff_seconds (2026-08-01,
        docs/DECISIONS.md): the original hardcoded 3-attempt, up-to-30s-per-
        attempt backoff was found live to compound into 10+ minutes of total
        wait on a heavily-throttled free-tier key (5 requests/minute) across
        a multi-step task -- each rate-limited step could individually wait
        up to ~60s, and several steps hitting the same per-minute cap back to
        back adds up fast. Made configurable via config.py's
        RATE_LIMIT_MAX_ATTEMPTS/RATE_LIMIT_MAX_BACKOFF_SECONDS rather than
        picking one fixed tradeoff for everyone: a user on a paid/high-quota
        plan may never hit this at all, while a free-tier user might
        reasonably prefer to fail fast (e.g. max_attempts=1) and see the
        real error immediately rather than wait. rate_limit_max_backoff_seconds
        caps whatever the server's own RetryInfo suggests -- pass None to
        trust the server's suggestion uncapped (the original behavior)."""
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._rate_limit_max_attempts = max(1, rate_limit_max_attempts)
        self._rate_limit_max_backoff_seconds = rate_limit_max_backoff_seconds
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

    def _generate_with_rate_limit_retry(self, user_content: str):
        """Isolates rate-limit handling from next_step()'s parse-failure
        retry loop below -- these are two genuinely different failure
        modes (a malformed response vs. the API refusing the call at all)
        and conflating them into one retry loop would make both harder to
        reason about. Raises the original exception once
        self._rate_limit_max_attempts is exhausted, or immediately for any
        non-429 API error (an auth failure or a 500 should never be
        silently retried the same way a rate limit is)."""
        last_exc: genai_errors.APIError | None = None
        for attempt in range(self._rate_limit_max_attempts):
            try:
                return self._client.models.generate_content(
                    model=self._model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                    ),
                )
            except genai_errors.APIError as exc:
                if getattr(exc, "code", None) != 429:
                    raise  # not a rate limit -- don't silently retry auth/server errors
                last_exc = exc
                if attempt < self._rate_limit_max_attempts - 1:
                    delay = _extract_retry_delay_seconds(exc)
                    if self._rate_limit_max_backoff_seconds is not None:
                        delay = min(delay, self._rate_limit_max_backoff_seconds)
                    print(
                        f"[warn] Gemini API rate limit hit (429 RESOURCE_EXHAUSTED) -- "
                        f"waiting {delay:.0f}s before retrying (attempt {attempt + 1}/"
                        f"{self._rate_limit_max_attempts}). If this happens often, you're on a "
                        f"free-tier quota (see the error message for exact limits) -- consider "
                        f"setting RATE_LIMIT_MAX_ATTEMPTS=1 in .env to fail fast instead of "
                        f"waiting, slowing down between tasks, or upgrading your plan."
                    )
                    time.sleep(delay)

        raise last_exc  # exhausted all attempts -- surface the real error rather than hang forever

    def next_step(
        self, instruction: str, screen_state: dict[str, Any], history: list[dict]
    ) -> dict[str, Any]:
        """Retries once on a parse failure (docs/DECISIONS.md 2026-08-01):
        Phase 7's first live browser run hit a real, observed failure mode
        -- Gemini's response was truncated mid-JSON (missing closing
        braces), which _parse_step correctly rejects rather than guessing
        at repair, but the ORIGINAL behavior let that single bad generation
        raise all the way out of run_task() and crash the whole process
        with an unhandled traceback. A second attempt on the exact same
        (instruction, screen_state, history) succeeded immediately when the
        user re-ran the same command by hand -- strong evidence this is
        transient generation variance, not a deterministic bug the retry
        would just repeat. Bounded to ONE retry, not unbounded, so a truly
        persistent failure (e.g. a real API outage) still surfaces as an
        error rather than looping/spending API calls silently forever.

        Rate-limit (429) handling is separated into
        _generate_with_rate_limit_retry() above -- see that method's
        docstring for why these are kept as two distinct retry concerns."""
        user_content = json.dumps(
            {
                "instruction": instruction,
                "current_state": screen_state,
                "steps_so_far": history,
            }
        )

        last_error: ValueError | None = None
        for attempt in range(2):  # one real attempt + one retry on parse failure
            response = self._generate_with_rate_limit_retry(user_content)
            self.last_call_cost = self._estimate_cost_from_response(response)
            raw_text = (response.text or "").strip()
            try:
                return _parse_step(raw_text)
            except ValueError as exc:
                last_error = exc
                if attempt == 0:
                    print(
                        f"[warn] Planner returned unparseable output on attempt 1 "
                        f"({exc}); retrying once before giving up."
                    )

        raise last_error  # both attempts failed -- surface the second attempt's error

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
        """Same bounded-retry-on-parse-failure behavior as
        HostedLLMPlanner.next_step -- see that method's docstring for why
        (docs/DECISIONS.md 2026-08-01). Applies here too since a local
        fine-tuned model can produce truncated/malformed output for the
        same reasons a hosted one can."""
        user_content = json.dumps(
            {
                "instruction": instruction,
                "current_state": screen_state,
                "steps_so_far": history,
            }
        )

        last_error: ValueError | None = None
        for attempt in range(2):
            raw_text = self._generate_fn(SYSTEM_PROMPT, user_content).strip()
            try:
                return _parse_step(raw_text)
            except ValueError as exc:
                last_error = exc
                if attempt == 0:
                    print(
                        f"[warn] Planner returned unparseable output on attempt 1 "
                        f"({exc}); retrying once before giving up."
                    )

        raise last_error


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
