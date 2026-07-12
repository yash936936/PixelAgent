# Decisions Log

This file is a running, append-only history of every decision made about the project — including every time
the AI writes a new file or overwrites an existing one. Nothing is deleted from this file; corrections are
made by adding a new dated entry, not editing old ones.

## Instructions for the AI (read every session)
- Before writing or overwriting **any** file in this project, add an entry here first (or immediately after,
  same turn) describing: what changed, why, and what it affects.
- Every entry MUST use the template below. No free-form entries.
- If a decision reverses or modifies a prior entry, reference the prior entry's date/title instead of
  silently contradicting it.
- Scope/safety-boundary decisions (see `context.md` hard boundaries) can be referenced but never silently
  overridden — a hard boundary can only change if the user explicitly asks in-session, and that request
  itself gets its own logged entry here before anything downstream changes.

## Entry template
```
### [YYYY-MM-DD] Title
- **Type:** New file / Overwrite / Design decision / Scope change
- **File(s) affected:** path(s)
- **What changed:**
- **Why:**
- **Impacts:** (which other files/docs need review as a result — check STATUS.md)
```

---

## Log

### [2026-07-09] Initial architecture decided
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/PHASES.md`
- **What changed:** Chose pixel-first control as the default execution path, with Playwright/API calls as
  an accelerated path underneath, rather than API-only automation.
- **Why:** Generalizes to apps/sites with no API (course platforms, internal tools, legacy desktop apps),
  matching the user's requirement to handle "any task I can perform on the laptop."
- **Impacts:** `PHASES.md` Phase 1/2 split (browser-first, then desktop pixel control).

### [2026-07-09] Excluded certification/exam auto-completion
- **Type:** Scope change
- **File(s) affected:** `context.md`, `docs/TRD.md`
- **What changed:** Removed "complete certification courses for me" from the feature set entirely.
- **Why:** Autonomous completion of graded coursework/exams misrepresents who actually earned the
  credential — this is credential fraud regardless of framing.
- **Impacts:** No repo mapped to this feature; excluded permanently per `TRD.md §6` hard boundaries.

### [2026-07-09] Excluded signup/verification bypass (FckSignups) and de-safetied model (G0DM0D3)
- **Type:** Scope change
- **File(s) affected:** `context.md`, `docs/TRD.md`
- **What changed:** Both repos removed from the feature/repo mapping.
- **Why:** FckSignups is built to defeat CAPTCHA/bot-detection/verification gates on third-party services —
  conflicts with acting as the user's honest agent rather than an abuse tool. G0DM0D3 is built to strip a
  model's safety training, which would break the confirmation-gate behavior the whole safety model depends
  on.
- **Impacts:** `TRD.md §6` hard boundaries; `docs/PHASES.md` never schedules either capability.

### [2026-07-09] Confirmation gate: approval required before irreversible/external actions
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/APPFLOW.md`, `docs/WORKFLOW.md`
- **What changed:** User selected "ask for confirmation before any irreversible/external action" over full
  autonomy or sensitive-only confirmation.
- **Why:** Explicit user choice.
- **Impacts:** `TRD.md §5` risk classification table; `src/confirmation/gate.py` design in `PHASES.md` Part
  1.4.

### [2026-07-11] Phase 2 implemented (all 3 parts)
- **Type:** New file (multiple) + Overwrite
- **File(s) affected:** `src/perception/ocr.py`, `src/perception/element_detector.py`,
  `src/perception/screen_diff.py` (new), `src/action/mouse_keyboard.py` (new),
  `src/action/action_router.py` (updated — added desktop branch), `src/brain/replanner.py` (new),
  `src/brain/orchestrator.py` (updated — added verify/replan loop), `src/main.py` (updated — wires
  MouseKeyboard/OCREngine/Replanner in), `requirements.txt` (added pytesseract, pillow, pyautogui), plus 5
  new test files (`tests/perception/test_element_detector.py`, `test_screen_diff.py`,
  `tests/action/test_mouse_keyboard.py`, `tests/brain/test_replanner.py`, `tests/brain/test_orchestrator.py`)
  and an expanded `tests/action/test_action_router.py`.
- **What changed:** Implemented every file listed in `PHASES.md` Parts 2.1–2.3. `ActionRouter` gained a
  `desktop` branch that resolves a click target either from explicit x/y or by OCR-locating `target_text`
  on a fresh screenshot. `Orchestrator` gained a verify step: it captures a before/after screenshot around
  each executed step and, on a mismatch (via `screen_diff.matches_expected`), hands the failure to
  `Replanner.correct()` for a corrected step, retried up to `Replanner`'s own `max_retries`. Verification is
  best-effort — if no screenshot source is configured (no `MouseKeyboard` and the browser screenshot fails),
  it's silently skipped rather than failing the task, so Phase 1-only configurations still work unchanged.
- **Why:** User requested Phase 2 implementation, part by part, with a deliverable zip.
- **Impacts:** `docs/STATUS.md` updated to reflect all Phase 2 files as Complete; `docs/DEBUG.md` gained a
  Phase 2 debug-pass entry. Phase 3 (memory) can now build on a stable `Orchestrator`/`ActionRouter`
  interface — no further signature changes anticipated for those two files in Phase 3 per `PHASES.md` Part
  3.1's description (only `episodic_store.py` lookups get added around the existing loop).

### [2026-07-11] Phase 4 implemented (self-improvement loop + research routing + loop audit accuracy)
- **Type:** New file (multiple) + overwrite (multiple)
- **File(s) affected:** `src/brain/research_router.py` (new), `src/brain/replanner.py` (updated),
  `src/memory/episodic_store.py` (updated), `src/memory/memory_api.py` (updated),
  `src/brain/orchestrator.py` (updated), `src/observability/logger.py` (updated),
  `src/brain/planner.py` (updated), `src/config.py` (updated), `src/main.py` (updated),
  `.env.example` (updated), plus `tests/brain/test_research_router.py`, `tests/brain/test_planner.py`,
  `tests/test_config.py`, and updates to `tests/brain/test_replanner.py` and
  `tests/brain/test_orchestrator_replay.py`.
- **What changed:**
  - `research_router.py`: new `ResearchTool` interface (`WebSearchTool`, `GitHubApiTool`) plus
    `ResearchRouter` that registers tools and routes a query to the first one whose `handles(platform)`
    matches, with a `doctor()` health-check per tool. No cookie-based login automation included, per
    `context.md`'s hard boundaries.
  - `replanner.py`: `review_and_learn()` rewritten to take `(instruction, original_step, edited_step,
    memory)` and write the correction to semantic memory via `MemoryAPI.set_site_quirk()` under a
    `corrections:<action>` namespace, keyed by the step's selector/url — a no-op if `memory` is `None` or
    the step wasn't actually edited.
  - `episodic_store.py` / `memory_api.py`: episodes now carry an `edited` flag (set when the user edited
    any confirmation-gate approval during that run); `flagged_for_review()` surfaces every task that either
    failed or was edited, for the self-improvement loop to inspect.
  - `orchestrator.py`: on any confirmation-gate edit (in both the fresh-planning loop and the Phase-3
    replay loop), calls `replanner.review_and_learn()` and marks the task `edited=True` when recording it
    to memory. Replay-executed steps are now logged with `llm_call=False` (added a `log_event()` on
    `Logger` for meta/marker records like "replay started" so they don't inflate `LoopAudit.step_count`
    either) — this is what makes the "fewer LLM calls on repeat tasks" success criterion from Phases 3/4
    actually visible in the trace log's audit summary.
  - `planner.py`: added `LocalPlanner` (optional local/fine-tuned model swap-in behind the same
    `PlannerBackend` interface, via an injected `generate_fn`) and `build_http_generate_fn()` (a stdlib-only
    HTTP transport helper for a local model server); extracted shared response parsing into `_parse_step()`
    so both backends validate identically.
  - `config.py` / `.env.example` / `main.py`: added `PLANNER_BACKEND` (`hosted` | `local`) and
    `LOCAL_PLANNER_ENDPOINT` config options; `main.py`'s new `_build_planner()` picks the backend — this
    never changes risk classification or confirmation gating, only where a proposed step comes from, per
    `docs/TRD.md §6`.
- **Why:** User requested Phase 4 implementation, part by part, with a deliverable zip.
- **Impacts:** `docs/STATUS.md` updated to mark all Phase 4 files Complete and bump overall progress to
  Phase 4. Full test suite re-run clean: 97/97 passing (75 from Phases 1-3 plus 22 new Phase 4 tests).
  `docs/PHASES.md`'s Phase 5 (`risk_classifier.py` rule-table expansion from real usage logs, plus
  `trace_replay.py`) is now the only remaining phase before hardening.

- **Type:** New file (multiple) + overwrite
- **File(s) affected:** `src/memory/episodic_store.py` (new), `src/memory/semantic_store.py` (new),
  `src/memory/memory_api.py` (new), `src/brain/orchestrator.py` (updated), `src/main.py` (updated), plus
  `tests/memory/test_episodic_store.py`, `tests/memory/test_semantic_store.py`,
  `tests/memory/test_memory_api.py`, `tests/brain/test_orchestrator_replay.py`, and `src/memory/__init__.py`
  / `tests/memory/__init__.py` package files.
- **What changed:** `episodic_store.py` persists (instruction, step plan, outcome, timestamp) per completed
  task in SQLite and exposes `find_match()`, a difflib-based near-duplicate lookup restricted to
  `status == "done"` episodes (threshold 0.82 on normalized instruction text). `semantic_store.py` is a
  namespaced SQLite key-value store for durable facts (a reserved `_preferences` namespace plus one
  namespace per site/app for learned UI quirks). `memory_api.py` is the single interface both stores go
  through, per `context.md`'s file map — `orchestrator.py` and `planner.py` never touch the stores directly.
  `orchestrator.py` now takes an optional `memory` param: before fresh planning, it calls
  `memory.find_replay()`; on a match it replays the stored step plan (still through the same risk
  classifier, confirmation gate, and verification/replan path as a freshly planned step — replay is a
  planning shortcut, never a safety shortcut), and falls back to fresh planning for any remaining steps on
  gate denial, execution error, or exhausted replan. Every completed task (replayed or freshly planned) is
  recorded back to `memory.record_task()`. `main.py` constructs a `MemoryAPI` from `cfg.log_dir` and passes
  it into `Orchestrator`, closing it after the run.
- **Why:** User requested Phase 3 implementation, part by part, with a deliverable zip.
- **Impacts:** `docs/STATUS.md` updated to mark all Phase 3 files Complete and bump overall progress to
  Phase 3. Full test suite re-run clean: 75/75 passing (51 from Phases 1-2 plus 24 new Phase 3 tests across
  `tests/memory/` and `tests/brain/test_orchestrator_replay.py`). No changes needed to `action/`,
  `perception/`, or `confirmation/` — Phase 3 only touches `memory/`, `brain/orchestrator.py`, and
  `main.py`, matching `docs/PHASES.md`'s file list for Phase 3 exactly (no deviation this time).

- **Type:** Overwrite (multiple)
- **File(s) affected:** `requirements.txt`, `.env.example`, `src/config.py`, `src/brain/planner.py`,
  `src/main.py`, `docs/TRD.md §2`
- **What changed:** `HostedLLMPlanner` now calls the Gemini API via the current `google-genai` SDK
  (`google.genai.Client`), not Anthropic's API. `Config.anthropic_api_key` renamed to `gemini_api_key`;
  `.env.example` now expects `GEMINI_API_KEY`; default model changed to `gemini-2.5-flash`. Also caught and
  avoided a real bug during this change: the first pass used the now-deprecated `google-generativeai`
  package, which raised a `FutureWarning` on import during re-verification — switched to the current
  `google-genai` package before finalizing.
- **Why:** User asked whether a free Claude API key exists — it doesn't (no persistent free tier on
  Anthropic's API); Gemini has a genuine free tier via Google AI Studio, so the user asked to swap the
  hosted planner backend to Gemini across every relevant file.
- **Impacts:** `PlannerBackend` interface (docs/CODE_LOGIC.md §4) is unchanged — this swap only touches the
  `HostedLLMPlanner` implementation, so Phase 4's local-model backend and the orchestrator/router/gate
  layers required no changes. Re-ran the full Phase 1 test suite (16/16 passing) and a clean import check
  after the swap; see `docs/DEBUG.md` for the entry.

### [2026-07-11] Phase 1 implemented (all 5 parts)
- **Type:** New file (multiple)
- **File(s) affected:** `requirements.txt`, `.env.example`, `src/config.py`, `src/brain/risk_classifier.py`,
  `src/brain/planner.py`, `src/brain/orchestrator.py`, `src/action/playwright_driver.py`,
  `src/action/action_router.py`, `src/confirmation/gate.py`, `src/confirmation/prompt_ui.py`,
  `src/observability/logger.py`, `src/main.py`, plus `tests/brain/test_risk_classifier.py`,
  `tests/action/test_action_router.py`, `tests/confirmation/test_gate.py`, and `__init__.py` package files.
- **What changed:** Implemented every file listed in `PHASES.md` Parts 1.1–1.5. One deviation from the
  original `PHASES.md` description: `orchestrator.py` routes execution through `ActionRouter` rather than
  calling `PlaywrightDriver` directly, to match `TRD.md §3.4`'s routing requirement and keep Phase 2's
  desktop-control branch a clean addition to `ActionRouter` instead of a rewrite of `orchestrator.py`.
- **Why:** User requested Phase 1 implementation, part by part, with a deliverable zip.
- **Impacts:** `docs/STATUS.md` updated to reflect all Phase 1 files as Complete; `docs/DEBUG.md` gained a
  real debug-pass entry (see that file); Phase 2 can now build directly on `ActionRouter`'s existing `web`
  branch by adding a `desktop` branch, per `PHASES.md` Part 2.2.

### [2026-07-09] Reviewed all 19 reference repos, created docs/CODE_LOGIC.md
- **Type:** New file
- **File(s) affected:** `docs/CODE_LOGIC.md` (new), `context.md` (file map + data sources sections),
  `docs/PHASES.md` (Phase 4 gained Parts 4.1 and 4.2), `docs/STATUS.md` (rows added)
- **What changed:** Went through every listed repo (including the 9 newly added since the prior session:
  ponytail, Agent-Reach, q-agent-harness, loop-engineering, pipecat, plus re-confirmation of
  TencentDB-Agent-Memory, cognee, PixelRAG, OpenManus, G0DM0D3, gbrain, OpenSpace, PraisonAI, Scrapling,
  openhuman, Playwright, playwright-mcp, langfuse, FckSignups, page-agent, UI-TARS-desktop, agent-browser,
  code-review-graph) and documented, per repo: what it does, the pattern extracted, and an original (not
  copied) code snippet mapped to a specific file in our `src/` tree. Two new `PHASES.md` additions
  resulted: `src/brain/research_router.py` (Phase 4, from Agent-Reach) and a `LoopAudit` addition to
  `src/observability/logger.py` (Phase 4, from loop-engineering).
- **Why:** User requested a full pass to extract core logic/patterns from every repo and centralize it as a
  build reference, without reproducing any repo's actual copyrighted source code verbatim.
- **Impacts:** `PHASES.md` Phase 4 scope grew (Parts 4.1/4.2); `STATUS.md` source-file table gained
  `research_router.py`; `context.md` file map and data-sources section now point to `CODE_LOGIC.md` as the
  authoritative repo mapping instead of an inline summary. G0DM0D3 and FckSignups re-confirmed excluded,
  consistent with the prior entries below — no reversal.

### [2026-07-09] Platform target: Windows desktop for v1
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/PHASES.md`
- **What changed:** User selected Windows desktop over macOS or cross-platform for v1.
- **Why:** Explicit user choice; cross-platform deferred to Phase 5+.
- **Impacts:** `PHASES.md` Phase 5 "revisit cross-platform support."

### [2026-07-11] Phase 5 hardening: risk_classifier.py rule-table expansion + new trace_replay.py
- **Type:** Overwrite (`src/brain/risk_classifier.py`) + New file (`src/observability/trace_replay.py`)
- **File(s) affected:** `src/brain/risk_classifier.py`, `src/observability/trace_replay.py` (new),
  `tests/brain/test_risk_classifier.py` (11 new cases), `tests/observability/test_trace_replay.py` (new,
  15 cases), `docs/STATUS.md`, `docs/DEBUG.md`.
- **What changed:** Expanded the Destructive/External keyword tables in `risk_classifier.py` with
  categories missed by the Phase 1 table (account deletion, drive/history wipes, subscription
  cancellation, DMs/invites, bookings/orders, app authorization, etc.), and added a conservative
  read-only-guard check so a step that only *inspects* a sensitive UI element (e.g. "check whether the
  delete button exists") isn't auto-escalated, while a step that still contains a real click/press verb
  alongside that phrasing still escalates correctly. Created `src/observability/trace_replay.py`
  (Phase 5, Part 5) — a dependency-free reader over a task's `.jsonl` log (written by
  `observability/logger.py`) that supports forward/backward stepping, jumping to an index, listing gate
  decisions (denied/edited), listing any step with a missing risk classification, and listing referenced
  screenshots in order, plus a minimal CLI entry point for manual use.
- **Why:** Directly implements `docs/PHASES.md` Phase 5 ("Hardening"): rule-table expansion "from real
  usage logs collected in Phases 1-4" and the new `trace_replay.py` file, per the user's request to
  implement Phase 5 part by part.
- **Impacts:** `STATUS.md`'s `risk_classifier.py` and `trace_replay.py` rows updated to Complete;
  `unclassified_or_missing_risk()` on `TraceReplay` gives a concrete, automatable way to check Phase 5's
  success criterion ("no unclassified/misclassified risk cases observed in a full regression pass"). No
  hard boundary or existing Phase 1-4 behavior was changed — all 97 pre-existing tests still pass
  unmodified, plus 24 new tests (121 total).

### [2026-07-12] Gap-remediation pass: fixes for every issue raised in independent review
- **Type:** Overwrite (multiple existing files) + New files
- **File(s) affected:**
  - `src/brain/boundary_guard.py` (NEW) — deterministic, non-negotiable hard-boundary check
    (graded-coursework submission, CAPTCHA/bot-detection bypass, signup-verification bypass) that
    runs before risk classification on every step and cannot be gated/edited around.
  - `src/brain/risk_llm_judge.py` (NEW) — actually implements the LLM risk-judge fallback that
    `risk_classifier.py`'s docstring had described since Phase 1 but that was never wired anywhere.
  - `src/brain/risk_classifier.py` — added `classify_with_confidence()` so callers can tell a real
    keyword match apart from an unmatched default, which is what the LLM fallback needs to know when
    to engage.
  - `src/brain/orchestrator.py` — wires `_check_boundary()` and `_classify_risk()` (keyword + optional
    LLM second opinion) into both the fresh-planning loop and the replay loop; fixed the verification
    screenshot scratch path to come from `config.py`'s `log_dir` instead of a hardcoded `"./logs/..."`
    string; verification failures are now logged via `log_event()` instead of silently swallowed;
    added `_gate_context()` so the confirmation prompt can actually show a screenshot path and account
    profile; added `_planner_cost()` so `LoopAudit.est_cost` reflects a real number instead of always
    `0.0`.
  - `src/brain/planner.py` — `HostedLLMPlanner` now reads real token usage off the Gemini response and
    estimates a real per-call cost (`estimate_cost_usd`), and exposes a raw `_generate_fn` transport so
    `risk_llm_judge.py` can reuse it without a second LLM client.
  - `src/confirmation/gate.py` / `src/confirmation/prompt_ui.py` — `GateContext` (screenshot path,
    account/profile) is now actually threaded through and displayed, matching what `docs/PHASES.md`
    Part 1.4 always specified but no prior implementation of `prompt_fn`'s signature could have shown.
  - `src/action/playwright_driver.py` — added a `profile_name` property so there's something for
    `GateContext.account_profile` to actually read.
  - `src/observability/logger.py` — added `_redact_step()`, applied in `log_step`/`log_gate_decision`/
    `log_event`, masking any params value whose key looks like a credential (password, secret, token,
    api_key, ssn, credit-card, cvv, etc.) before it's ever written to the plaintext `.jsonl` trace —
    directly implements the "no plaintext storage of user credentials" requirement in `docs/TRD.md §4`,
    which nothing previously enforced.
  - `src/memory/episodic_store.py` — `Episode` now carries `match_score`, and `orchestrator.py` logs it
    on every replay attempt, so replay confidence is now auditable from the trace instead of being an
    opaque yes/no decision.
  - `requirements.txt` — every dependency pinned to an exact version that has actually been installed
    and run against this test suite in this environment (was previously all lower-bound-only `>=`,
    which caused a real `ImportError` from an ambiguous `google-genai` install during this very pass).
  - `src/main.py` — wires `log_dir` and a `llm_risk_judge` (built from whichever planner backend is
    configured) into `Orchestrator`.
  - New/expanded tests: `tests/brain/test_boundary_guard.py`, `tests/brain/test_risk_llm_judge.py`,
    `tests/observability/test_logger.py`, `tests/confirmation/test_prompt_ui.py`, `tests/test_main.py`,
    plus additions to `test_risk_classifier.py`, `test_orchestrator.py`, `test_gate.py`,
    `test_planner.py`, `test_episodic_store.py`.
- **Why:** Directly addresses every concrete gap raised in an independent line-by-line review of the
  codebase: (1) the promised LLM risk-fallback never existing, (2) hard boundaries being enforced only
  by hoping the LLM planner refused, (3) `prompt_ui.py` never actually showing the screenshot/profile
  context the docs always claimed it showed, (4) `LoopAudit.est_cost` always being `0.0`, (5) a
  hardcoded screenshot path bypassing `config.py`, (6) verification failures being silently swallowed
  with zero trace, (7) credentials being written to plaintext logs with no redaction, (8) unpinned
  dependencies risking exactly the kind of install drift this project hit firsthand, and (9) episodic
  replay's match confidence being thrown away instead of logged.
- **Impacts:** 165 tests passing (up from 121; 44 new, all previously-passing tests still green and
  unmodified in behavior). See `docs/DEBUG.md` for the debug pass covering this remediation, and
  `docs/STATUS.md`'s Known Gaps section for what remains honestly unresolved (live validation, full
  screenshot/log encryption at rest, multi-user/concurrency, and the inherent limits of a keyword-based
  boundary guard against sufficiently novel phrasing or prompt injection).
