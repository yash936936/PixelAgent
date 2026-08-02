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

### [2026-07-12] Track B: two separate trained-model interfaces + mandatory eval gate + training scaffold
- **Type:** New files + overwrites
- **File(s) affected:**
  - `src/brain/risk_model_backend.py` (NEW) — `RiskModelBackend` interface, deliberately NOT sharing a
    class hierarchy with `PlannerBackend`, with `HostedRiskJudge` and `LocalFineTunedRiskModel`
    implementations. Additive-only by construction: can escalate Local -> External/Destructive, can
    never downgrade a keyword match, never overrides `boundary_guard.py`.
  - `src/brain/planner.py` — renamed `LocalPlanner` to `LocalFineTunedPlanner` (matching the name
    `docs/CODE_LOGIC.md §4` used from the start), kept `LocalPlanner` as a backward-compat alias.
  - `src/config.py` — added `risk_model_backend` ("none"|"hosted"|"local", default `"none"`) and
    `local_risk_model_endpoint`, deliberately separate config keys from `planner_backend`/
    `local_planner_endpoint` so the two models can be swapped/rolled back independently.
  - `src/main.py` — replaced the old `_build_llm_risk_judge()` (which derived a risk judge from
    whichever planner happened to be configured) with `_build_risk_model_judge(cfg)`, which builds a
    genuinely separate model from its own config block. Defaults to `None` (keyword-only floor) unless
    explicitly enabled.
  - `eval/adversarial_cases.jsonl` (NEW) — 30 curated adversarial/evasive-phrasing test cases across 4
    categories: `evasive_destructive`, `evasive_external`, `boundary_evasion`, `benign_but_tricky`.
  - `eval/adversarial_boundary_eval.py` (NEW) — the harness itself. Scores the current keyword-only
    baseline (`boundary_guard.py` + `risk_classifier.py`) and, optionally, a `RiskModelBackend` layered
    on top, exactly the way `orchestrator.py`'s `_classify_risk()` actually does it. Reports
    **per-category recall**, not just overall accuracy, deliberately, since averaging would hide a low
    recall on the highest-stakes category behind higher scores elsewhere.
  - `eval/README.md` (NEW) — documents proposed deployment-gate thresholds (recall ≥ 0.95 for
    `evasive_destructive`/`boundary_evasion`, ≥ 0.90 for the other two categories) and states plainly
    that these are a starting proposal needing human sign-off, not an external standard.
  - `training/` (NEW directory) — `README.md` (two-separate-runs overview + recommended base models:
    Qwen2.5-3B/7B-Instruct or Llama-3.2-3B-Instruct), `prepare_dataset.py` (converts eval cases +
    real episodic-store data into instruction-tuning jsonl for either target), `train_lora.py` (LoRA
    fine-tuning script, heavy deps deferred via lazy imports so the module still imports cleanly
    without them installed), `model_card_template.md` (the auditability record required by
    `docs/TRD.md §6.1`), `requirements-training.txt` (kept separate from the main `requirements.txt`
    on purpose — training deps are heavyweight and machine-specific).
  - `docs/TRD.md` — added §6.1 making trained-model provenance auditable via the model card + eval gate
    rather than merely asserted.
  - New/updated tests: `tests/brain/test_risk_model_backend.py`, `tests/eval/test_adversarial_boundary_eval.py`,
    `tests/training/test_prepare_dataset.py`, `tests/training/test_train_lora.py`, `tests/test_main.py`
    (rewritten for the new config-driven builder).
- **Why:** Implements the two-model architecture requested: a lower-stakes planner model and a
  higher-stakes risk/boundary model, kept as genuinely separate classes/configs/training runs rather
  than one model doing double duty, plus the eval harness built and run BEFORE any deployment decision
  rather than after.
- **Notable finding during this pass:** running the freshly-built eval harness against the existing
  read-only-guard logic in `risk_classifier.py` immediately caught a real bug — `_has_actual_verb()` was
  checking the combined `"{action} {description}"` text, and the `action` field itself (e.g. `"click"`)
  is one of the verbs the check looks for, so the guard silently passed for every step routed as
  `action="click"` regardless of what its description said. Fixed to check the description text alone,
  and to scan every occurrence of a keyword rather than just the first (a second bug the fix's first
  iteration introduced and the harness caught again immediately). This is exactly the kind of gap this
  harness exists to surface — see `docs/DEBUG.md`'s entry for this date for the full trace of both fixes.
- **Impacts:** 189 tests passing (up from 165; 24 new). The eval harness's baseline run against the
  keyword-only floor scores ~40% overall accuracy with single-digit-to-mid per-category recall on
  `evasive_destructive` and `boundary_evasion` specifically — this is the expected, honest starting
  point that justifies training a risk model in the first place, documented in `eval/README.md` rather
  than glossed over. `risk_model_backend` defaults to `"none"` — nothing about this pass changes
  runtime behavior unless a human explicitly opts in via `.env`, and doing so before the eval gate is
  cleared is a documented misuse of the config, not something the code can prevent by itself.

### [2026-07-12] Design system replaced: console color scheme -> "Steep" token system
- **Type:** Overwrite + New file (multiple)
- **File(s) affected:** `docs/DESIGN.md` (overwritten), `docs/design-tokens/tokens.json` (new),
  `docs/design-tokens/variables.css` (new), `docs/design-tokens/theme.css` (new),
  `docs/design-tokens/DESIGN_source.md` (new), `context.md` (file map entry updated)
- **What changed:** The old `DESIGN.md` (amber/red/green console-prompt palette) is fully replaced by a
  user-supplied design token system ("Steep" — near-monochrome, Signifier serif + Sohne sans, single peach
  accent, pill buttons, 24px card radius). Raw token files are preserved verbatim under
  `docs/design-tokens/` as the machine-readable source of truth; `docs/DESIGN.md` is now a narrative layer
  distilling those tokens for Pixel-Agent-specific use, including a new Risk-State Mapping table that
  reconstructs the old External/Destructive/Success/Denied visual distinctions using only tokens from this
  system (since it has no built-in red/amber/green) — External uses ink-black-on-peach, Destructive uses
  sienna-brown-on-peach, both always paired with a text label per the existing color-plus-label
  accessibility rule.
- **Why:** User provided a specific design system (tokens.json/variables.css/theme.css/style-reference md)
  and instructed that it be used strictly for all future UI work, replacing the ad hoc console scheme.
- **Impacts:** Any future GUI implementation (dashboard, confirmation prompt, trace viewer) must be built
  from `docs/design-tokens/tokens.json` values only — this is now enforced by instruction in `context.md`'s
  file map, not just by convention. No source code changes yet; no GUI has been implemented in `src/` as of
  this entry.

### [2026-07-12] Adopted uploaded "Track B" project as the working codebase, replacing the in-progress
Phase 3 build
- **Type:** Overwrite (whole-project replacement)
- **File(s) affected:** entire project tree (previous partial Phase 3 work backed up separately, not
  deleted)
- **What changed:** The user supplied a more advanced, independently-developed version of this project
  (received as `pixel-agent-trackb.zip`) that already includes Phase 3 (memory), a Phase 4 "Track B"
  addition (a separate, additive-only `RiskModelBackend` alongside the existing keyword `risk_classifier.py`
  and a `boundary_guard.py`), an adversarial evaluation harness (`eval/`), and LoRA fine-tuning scaffolding
  for two independent models (`training/`) — none of which had been built yet in this session's own Phase 3
  work-in-progress. This was adopted as the new working codebase.
- **Why:** User uploaded it and referred to it as "the above system" to test and build a GUI for; it is
  substantially further along (189 passing tests vs. this session's 51 at the end of Phase 2) and was
  clearly built with the same architecture, hard boundaries, and file-map conventions this project's own
  `docs/` establish, so adopting it is a continuation, not a divergence.
- **Impacts:** All Phase 3/4-related `docs/STATUS.md`, `docs/PHASES.md`, `docs/CODE_LOGIC.md`, and
  `docs/DECISIONS.md` content now reflects the uploaded project's own history (its `DECISIONS.md` entries
  are kept as-is above this one, not rewritten). Verified in this session: clean venv + exact pinned
  `requirements.txt` install succeeds, all 189 tests pass, all 29 `src/` modules import cleanly, and
  `eval/adversarial_boundary_eval.py`'s baseline run reproduces the documented ~40% overall /
  14% evasive-category accuracy — confirming the project's own claims rather than taking them on faith.

### [2026-07-12] Native Windows GUI implemented (PySide6, full dashboard)
- **Type:** New file (multiple) + Overwrite (2 memory files, per below)
- **File(s) affected:** `src/gui/style.py`, `src/gui/app.py`, `src/gui/main_window.py`,
  `src/gui/worker.py`, `src/gui/gui_logger.py`, `src/gui/widgets/{task_composer,trace_panel,stats_panel,
  memory_panel,confirmation_dialog}.py` (all new), `requirements-gui.txt` (new, kept separate from
  `requirements.txt` so CLI-only installs stay lean), `src/memory/semantic_store.py` (added
  `all_preferences()`), `src/memory/memory_api.py` (added `all_preferences()` facade), plus 8 new test
  files under `tests/gui/` and additions to `tests/memory/test_semantic_store.py` and
  `tests/memory/test_memory_api.py`.
- **What changed:** Built a native Windows desktop dashboard per the user's explicit choices (PySide6, full
  dashboard scope: task input + live trace + memory browser + LoopAudit stats). Every color/font/spacing
  value is loaded from `docs/design-tokens/tokens.json` through `src/gui/style.py` — nothing hardcoded.
  `ConfirmationDialog` implements the exact `prompt_fn(step, risk, context) -> GateDecision` contract
  `ConfirmationGate` already expected (that contract, including the `GateContext` fallback handling, was
  already in place in `gate.py`/`console_prompt.py` before this session — the GUI is the second, not first,
  implementation of it). `TaskWorker` runs `Orchestrator.run_task()` on a background `QThread`; the
  confirmation gate crosses back to the GUI thread via `GateBridge`, which uses a
  `Qt.BlockingQueuedConnection` signal — the worker thread's call to `gate.request_approval()` genuinely
  blocks until the user closes the dialog, matching the exact synchronous semantic the rest of the
  orchestrator loop already assumes.
- **Why:** User requested a native Windows GUI (PySide6) showing a full dashboard, ahead of GPU training
  (per the stated plan: build the GUI now, train models later once real usage data exists).
- **Two real bugs found and fixed during this pass, not just written and shipped:**
  1. `MemoryPanel` initially reached into `MemoryAPI._semantic` (a private attribute) to list preferences —
     violated `memory_api.py`'s own stated rule that "nothing else should import the store classes
     directly." Fixed by adding a proper public `all_preferences()` method to both `SemanticStore` and
     `MemoryAPI`, with new tests for both.
  2. `ConfirmationDialog._on_approve()` originally used `self._edit_box.isVisible()` to detect whether the
     user had opened the edit field — this is unreliable because Qt's `isVisible()` reflects actual
     on-screen visibility (dependent on the whole window being shown), not just the widget's own
     `setVisible()` call, so it silently failed whenever the dialog was tested or driven without a real
     `.exec()`/`.show()` call. Caught by `tests/gui/test_confirmation_dialog.py`'s edit-box test failing on
     first run. Fixed with an explicit `_edit_mode` boolean flag instead of relying on Qt visibility state.
- **Impacts:** `docs/STATUS.md` and `docs/DEBUG.md` updated. The cross-thread `GateBridge` mechanism was
  specifically stress-tested with a real `QThread` (not just mocked) to rule out a deadlock, since a wrong
  connection type there would hang the whole app on the first External/Destructive step — see
  `tests/gui/test_gate_bridge.py`. GPU model training (per the user's stated plan) remains untouched and
  still blocked on real usage data, unchanged by this GUI work.

### [2026-07-13] Fixed real profile-launch bug found via a live GUI run, removed Est. cost from GUI
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/action/playwright_driver.py`, `src/gui/widgets/stats_panel.py`,
  `.env.example`, plus new `tests/action/test_playwright_driver.py` and updates to
  `tests/gui/test_stats_panel.py`
- **What changed:**
  1. **Real bug, found by the user's own first live task run** (not caught by any prior unit test, because
     no test exercised the actual Playwright launch call): `PlaywrightDriver.__init__` was building
     `user_data_dir` as `profiles_dir / profile_name` (e.g. `...\User Data\Profile 3`) and handing that
     whole path straight to `launch_persistent_context`. Chromium treats whatever directory it's given as
     the *entire* user-data root and looks for a `Default` profile inside it — since no such subfolder
     existed inside `...\Profile 3\`, Chromium silently created a brand-new, empty, logged-out profile
     there instead of opening the user's real, already-logged-in "Profile 3". This is exactly what the
     screenshots showed: Pixel landed on Gmail's public marketing page and had to be told to click
     "Sign in," instead of opening the real inbox. Fixed by passing `user_data_dir` as the real Chrome
     "User Data" **root** and selecting the profile via the `--profile-directory=<name>` launch arg
     instead — the same mechanism real Chrome itself uses to open a specific profile from a shared root.
     Also wrapped the launch call so a failure (most commonly: the real Chrome still running on that same
     profile, blocking Playwright via its lock file) raises a new `ChromeProfileLaunchError` with an
     actionable message instead of a raw Playwright exception.
  2. Removed the "Est. cost ($)" stat card from `StatsPanel` per explicit user request. `LoopAudit` still
     computes and logs `est_cost` internally (unchanged) — only the GUI display was removed, not the
     underlying tracking, since other consumers (the trace log file, a future export) may still want it.
- **Why:** User uploaded screenshots of the GUI's first real live run, which surfaced the profile bug
  directly, and asked to check `.env` for problems and remove the cost display.
- **Impacts:** `.env.example` rewritten with an explicit, corrected explanation of what `PROFILES_DIR` must
  actually point at (the Chrome "User Data" root, not a Pixel-owned or profile-specific folder) and a
  reminder that real Chrome must be fully closed before running Pixel. This is the first bug in this
  project actually caught by a live run rather than by a unit test or code review — a good illustration of
  why `docs/STATUS.md` has consistently flagged "zero live task runs" as the single biggest blocker: this
  exact class of bug (correct-looking code that's wrong about an external system's actual behavior) cannot
  be caught any other way.

### [2026-08-01] Zero-dependency semantic risk/boundary layer + real-pixel integration harness + real OCR bug found and fixed
- **Type:** New (multiple) + Overwrite (`src/perception/ocr.py`)
- **File(s) affected:** `src/brain/semantic_matcher.py` (new), `src/brain/risk_model_backend.py` (updated —
  adds `SemanticRiskJudge`, `semantic_boundary_match`), `eval/adversarial_boundary_eval.py` (updated —
  adds `--model semantic`), `eval/README.md` (updated), `src/perception/ocr.py` (overwritten — bug fix),
  `tests/brain/test_semantic_matcher.py` (new), `tests/brain/test_semantic_risk_judge.py` (new),
  `tests/perception/test_ocr_solid_background_regression.py` (new), `tests/integration/` (new: `conftest.py`,
  `test_real_ocr_pipeline.py`, `test_real_screen_diff.py`, `fixtures/pages/*.html`).
- **What changed:**
  1. **Semantic risk/boundary layer.** `risk_classifier.py`/`boundary_guard.py` are keyword/substring
     matchers, and `eval/adversarial_boundary_eval.py` already proved the resulting gap: ~40% overall,
     14% recall on `evasive_destructive`/`boundary_evasion` specifically — exactly the categories
     phrased to avoid every literal keyword by construction. Rather than wait for Track B's trained
     model (blocked on a GPU and real usage data, per `docs/STATUS.md`), added a same-day intermediate:
     `semantic_matcher.py` implements dependency-free character-n-gram cosine similarity (no numpy,
     no embedding model download, no network call), and `risk_model_backend.py`'s new
     `SemanticRiskJudge`/`semantic_boundary_match` score a step's text against small, hand-written
     exemplar phrase banks — deliberately written independently of `eval/adversarial_cases.jsonl` so
     the eval isn't cheated. Result on the adversarial eval: 40% → 73% overall,
     `evasive_destructive`/`boundary_evasion` recall 14% → 71% each, `evasive_external` 62% → 88%,
     `benign_but_tricky` unchanged at 62% (verified no regression after adding a read-only-framing
     guard mirrored from `risk_classifier.py`'s own guard, since the raw semantic layer initially
     introduced a false positive on "check if the delete button exists"-style inspection phrasing).
     Both new classes fail open (return `None`/no opinion below threshold) — same contract as
     `HostedRiskJudge`/`LocalFineTunedRiskModel` — and are explicitly documented as NOT a replacement
     for Track B's eventual trained model or its deployment gate (see `eval/README.md`'s 2026-08-01
     update).
  2. **Real-pixel integration test harness (`tests/integration/`).** Every one of this project's 213
     unit tests exercises `OCREngine`/`element_detector`/`screen_diff` against synthetic, hand-built
     data (`OCRWord` lists constructed by hand, solid-color `PIL.Image` objects) — `docs/STATUS.md` has
     flagged "zero live validation" as the single biggest blocker since Phase 5. Rather than wait for
     the user's real Windows machine, added an offline-but-real proxy: local HTML fixture pages
     (`tests/integration/fixtures/pages/`) rendered by a real headless Chromium via Playwright, real
     screenshots piped through the real Tesseract binary and real `screen_diff.compare()` — no mocks
     anywhere in that chain. Mirrors the existing `tests/gui/` convention of a tier that needs an
     optional dependency (`pytest --ignore=tests/integration` if Playwright/Tesseract aren't
     available).
  3. **Real bug found by the harness above, on its very first run — not a hypothetical, an actual
     failure.** `test_real_ocr_pipeline.py` failed immediately: Tesseract found zero words at all on a
     standard solid-blue "Submit" button with white text, an extremely common real-UI pattern that no
     prior test could have caught since none exercised the real Tesseract binary. Root cause, confirmed
     by isolating a crop of just the button (an inverted, upscaled crop still failed identically at the
     full-page level): it was not a color-contrast problem, it was Tesseract's `textord` layout-analysis
     pass discarding the solid-color rectangle as a non-text "picture" block *before* OCR runs, a
     document-scanning heuristic that misfires on real UI screenshots (solid buttons, colored panels,
     dark-mode surfaces) regardless of what text is drawn on them. Fixed with a single Tesseract config
     parameter, `-c textord_min_linesize=1.0`, verified empirically to find both the label and the
     button text with no changes needed to image scale, color inversion, or page-segmentation mode.
     Added `tests/perception/test_ocr_solid_background_regression.py` — a fast, mock-free regression
     test using a small synthetically-drawn solid-button image (no Playwright/Chromium needed) that pins
     this specific bug down permanently.
- **Why:** Continuation of the independent architectural review from earlier in this session (drawbacks/
  gaps discussion) — the two highest-leverage, same-day-feasible items identified were (a) closing some of
  the keyword-classifier evasion gap without waiting on GPU training, and (b) proving the perception layer
  against real pixels instead of only synthetic data, precisely because "zero live validation" had been an
  open, honestly-documented blocker for this entire project's history.
- **Impacts:** 213 → 221 tests passing (18 new for the semantic layer, 6 new real-pixel integration tests,
  2 new OCR regression tests). `docs/STATUS.md`'s "zero live validation" known gap is now partially closed
  — real Tesseract OCR and real `screen_diff` have been exercised against real rendered pixels for the
  first time in this project's history, and it immediately surfaced a genuine bug. What remains unproven:
  real OS-level mouse/keyboard control, real DPI/multi-monitor scaling, and a real Gemini API call — all
  still require the user's actual Windows machine, unchanged by this pass. `docs/PHASES.md` intentionally
  not restructured — this work follows the same convention as the earlier GUI/Track-B additions (tracked
  in `STATUS.md`/`DECISIONS.md` directly rather than inserted as a new numbered phase in a doc meant to
  define file structure ahead of implementation).

### [2026-08-01] Phase 6 — semantic risk/boundary layer actually live-wired into the orchestrator
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/config.py`, `src/main.py`, `src/brain/orchestrator.py`,
  `tests/test_config.py`, `tests/test_main.py`, `tests/brain/test_orchestrator.py`.
- **What changed:** The previous entry (also dated 2026-08-01) built `SemanticRiskJudge` and
  `semantic_boundary_match`, proven only via `eval/adversarial_boundary_eval.py --model semantic` — the
  live orchestrator had no path to either. Closed that gap:
  1. `config.py`: `risk_model_backend` now accepts `"semantic"` alongside `"none"/"hosted"/"local"`, with
     no new endpoint field required (it's in-process, unlike `"local"`).
  2. `main.py`'s `_build_risk_model_judge()`: new branch returns `SemanticRiskJudge().judge` for
     `RISK_MODEL_BACKEND=semantic` — wired the exact same way `llm_risk_judge` already gets passed to
     `Orchestrator` for `"hosted"`/`"local"`, so this reuses the existing escalation path in
     `orchestrator._classify_risk()` rather than adding a new one.
  3. `orchestrator.py`'s `_check_boundary()`: `semantic_boundary_match()` now runs as an always-on second
     layer after the keyword `boundary_guard.check()` — consulted only when the keyword layer found
     nothing (so it can only add stops, never remove or downgrade one), and both layers' verdicts are
     logged with a `detected_by: "keyword" | "semantic"` field so a reviewer can tell which layer actually
     caught a given case. This mirrors `boundary_guard.py`'s own "cannot be disabled by config" design —
     there is no config knob to turn either boundary layer off.
- **Why:** Phase 6 of the post-hardening roadmap (`docs/PHASES.md`) — this was flagged as the single
  highest-leverage, lowest-cost open item in the 2026-08-01 status report: the eval score improvement
  (40% → 73% overall) was real but inert on any actual task run until wired in.
- **Impacts:** 221 → 229 tests passing (+8: 4 `test_config.py` covering the new `"semantic"` value and
  existing `"local"`/invalid-value validation which had no prior coverage, 1 `test_main.py` proving the
  new builder branch returns a working judge with no endpoint needed, 2 `test_orchestrator.py` proving the
  semantic boundary layer both catches a paraphrase the keyword layer misses and stays silent/non-double-
  logged when the keyword layer already caught something, 1 end-to-end `test_orchestrator.py` test proving
  `SemanticRiskJudge` wired exactly as `main.py` now wires it actually reaches the confirmation gate with
  the escalated risk tier and produces a real `llm_risk_escalation` log event). `docs/PHASES.md`'s Phase 6
  marked complete. Phase 7 (first real live validation on Windows) remains the next item, unchanged by
  this pass — none of Phase 6's wiring has been exercised against a real Gemini call or real user-facing
  confirmation dialog, only against mocks, same caveat as every other orchestrator-level test in this
  project prior to a real live run.

### [2026-08-01] Phase 7 prep — pre-flight doctor tool + live-run checklist (not the live run itself)
- **Type:** New
- **File(s) affected:** `src/doctor.py` (new), `tests/test_doctor.py` (new),
  `docs/PHASE_7_CHECKLIST.md` (new).
- **What changed:** Phase 7 (`docs/PHASES.md`) requires the user's actual Windows machine and cannot be
  executed or verified from this build environment. Rather than leave it as an unstructured "go run it and
  see," added `python -m src.doctor` — a pre-flight diagnostic that checks every environment prerequisite
  (Tesseract binary on PATH, Playwright Chromium launches, `GEMINI_API_KEY`/config loads, `profiles_dir`/
  `log_dir` writable, Phase 6's semantic layer working) without executing any real task, click, or
  destructive action. Desktop-control/display availability is checked but marked `optional` — mirrors
  `main.py`'s own existing `_build_desktop_backends()` graceful-degradation behavior (browser-only tasks
  still work without a real display). An `--live` flag makes one real, minimal Gemini API call to confirm
  the key works end-to-end; without it, the tool costs nothing to run repeatedly while debugging setup.
  `docs/PHASE_7_CHECKLIST.md` gives the step-by-step live-run sequence (doctor tool → Chrome profile
  verification per the 2026-07-13 profile-bug lesson → browser-only task first → desktop-target-type task
  → capture the trace log → report back), explicitly ordered to validate the already-partially-proven
  browser path before the completely untested desktop path.
- **Why:** Phase 7 is the first phase in this project's history that fundamentally cannot be completed or
  verified by an agent working in a build sandbox — it requires real hardware the user must operate
  directly. This is the highest-leverage thing to prepare in the meantime: front-loading environment-setup
  failures (missing Tesseract, wrong Chrome profile path, no Playwright browsers installed) into a 5-second
  local check rather than discovering them mid-live-run, and giving Phase 7 a concrete, ordered checklist
  instead of leaving "run it and see what happens" underspecified.
- **Impacts:** 229 → 240 tests passing (+11, all against mocked Tesseract/Playwright/pyautogui — the
  doctor tool's own logic is fully testable without real hardware even though what it checks isn't). Phase
  7 itself is NOT complete — this entry only records the preparation for it. The actual live run, and
  everything Phase 7's success criterion requires, still needs to happen on the user's machine and be
  reported back before `docs/PHASES.md`'s Phase 7 can be marked complete.

### [2026-08-01] TESSERACT_CMD env var wired through — real gap found by the doctor tool's first real use
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/config.py`, `src/main.py`, `src/doctor.py`, `.env.example`,
  `tests/test_config.py`, `tests/test_doctor.py`.
- **What changed:** The doctor tool (added earlier today) was run for the first time on the user's real
  Windows machine and immediately found a genuine, real environment gap: Tesseract is installed but not on
  PATH — and `OCREngine()` in `main.py` had no way to point at it directly; `tesseract_cmd` existed as a
  constructor parameter but nothing in `config.py`/`main.py` ever passed a value into it, so the only fix
  available before this was editing PATH. Added `TESSERACT_CMD` as a proper config option:
  `config.py`'s `Config.tesseract_cmd` (defaults to `None`, unchanged PATH-reliant behavior),
  `main.py`'s `_build_desktop_backends()` now takes `cfg` and passes `cfg.tesseract_cmd` through to
  `OCREngine(tesseract_cmd=...)`, and `src/doctor.py`'s `check_tesseract()` now checks the same
  `TESSERACT_CMD` value the real run would use, rather than only ever checking PATH — so the doctor tool
  and the actual app now agree on what "working" means. `.env.example` documents the new variable with the
  typical Windows install path.
- **Why:** Direct result of using the Phase 7 prep tooling for its actual intended purpose — the doctor
  tool caught exactly the kind of environment-setup problem it was built to catch, on its very first real
  run, and the fix it pointed toward (`OCREngine(tesseract_cmd=...)`) didn't actually exist as a usable
  config path yet. Fixed immediately rather than just telling the user to edit their system PATH.
- **Impacts:** 240 → 244 tests passing (+4: default-is-None, value-is-loaded-when-set in `test_config.py`;
  explicit-path-success and explicit-path-failure-hint in `test_doctor.py`). This is still Phase 7 prep,
  not Phase 7 itself — the user has not yet completed a live task run; this entry exists because it's a
  real code gap found and fixed, following the same standard as every other entry in this log.

### [2026-08-01] Phase 7 — first real live runs, two real bugs found and fixed
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/brain/planner.py`, `src/action/action_router.py`,
  `tests/brain/test_planner.py`, `tests/action/test_action_router.py`.
- **What changed:** The user completed the first real live task runs in this project's history (browser
  task and desktop task, per `docs/PHASE_7_CHECKLIST.md`) and hit two genuine, previously-invisible bugs —
  neither could have been caught by any mock, exactly as expected for the first phase run against real
  hardware:
  1. **Browser task crashed the whole process on a truncated Gemini response.** `_parse_step()` correctly
     rejected malformed JSON (missing closing braces mid-response), but `HostedLLMPlanner.next_step()` let
     that `ValueError` propagate straight out of `run_task()` as an unhandled traceback. Re-running the
     exact same command by hand succeeded immediately — strong evidence of transient generation variance,
     not a deterministic bug. Fixed with a bounded (one) retry inside `next_step()` for both
     `HostedLLMPlanner` and `LocalFineTunedPlanner`: on a parse failure, log a warning and try once more
     before raising, so isolated bad generations no longer crash a task outright, while a genuinely
     persistent failure (e.g. a real API outage) still surfaces as an error rather than retrying forever.
  2. **Desktop task failed on the very first click.** The planner emitted
     `{"action": "click", "target_type": "desktop", "params": {"selector": "Start button"}}` for the
     Windows Start button — but `action_router.py`'s desktop click path requires `target_text` or explicit
     `x`/`y`, never `selector` (that key is only meaningful for `target_type="web"`, where
     `PlaywrightDriver.click()` takes a CSS selector). Root cause: `SYSTEM_PROMPT`'s example schema showed
     one blended example (`{"selector": "...", "text": "..."}`) that never actually distinguished the two
     target types' different param shapes. Fixed two ways, deliberately layered: (a) rewrote
     `SYSTEM_PROMPT` to spell out the web vs. desktop param schemas explicitly and separately, and (b)
     added a defensive fallback in `action_router.py`'s `_resolve_coords()` — if a desktop click step still
     arrives with `selector` instead of `target_text` (prompt compliance is never guaranteed, only
     encouraged), treat `selector`'s value as `target_text` rather than failing the whole task, since it's
     clearly the same underlying intent (click the thing labeled with this text) expressed with the wrong
     key name. This is a naming normalization only — it changes nothing about which risk/boundary checks
     already ran upstream in `orchestrator.py` before this method is ever reached.
- **Why:** This is exactly what Phase 7 (`docs/PHASES.md`) exists to surface — real bugs no mock-based test
  suite could have found, on the first real hardware run in the project's history, matching the pattern of
  the 2026-07-13 profile-launch bug and the 2026-08-01 OCR `textord_min_linesize` bug before it.
- **Impacts:** 244 → 249 tests passing (+5: 3 `test_planner.py` covering retry-then-succeed for both
  backends and bounded-retry-still-raises-on-persistent-failure; 2 `test_action_router.py` covering the
  `selector`→`target_text` fallback and confirming `target_text` still wins when both keys are present).
  **Phase 7's success criterion is now substantially met**: one browser task and one desktop-target-type
  task have both been attempted end-to-end on real Windows hardware, with real trace logs inspected and
  two real issues found and fixed as a direct result. The desktop task's original run ended in
  `status: error` — the user has not yet re-run it against these fixes to confirm a full desktop task
  completes cleanly end-to-end; that confirmation, not just the fixes existing, is what should actually
  close out Phase 7 in `docs/PHASES.md`.

### [2026-08-01] First fully-completed desktop task — and two more real bugs found and fixed
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/confirmation/prompt_ui.py`, `src/action/mouse_keyboard.py`,
  `src/action/action_router.py`, `src/brain/planner.py`, `tests/confirmation/test_prompt_ui.py`,
  `tests/action/test_mouse_keyboard.py`, `tests/action/test_action_router.py`.
- **What changed:** The user re-ran the desktop task ("open Notepad and type a test message") against the
  previous entry's fixes and it completed with `status: done` — the first fully-completed desktop task in
  this project's history, confirming `target_text`-based click resolution works correctly on real Windows
  hardware. But the trace and terminal transcript revealed two more real, previously-invisible bugs:
  1. **The confirmation gate silently approved an invalid answer.** At the third prompt the user typed
     `Notepad` (a typo, not `A`/`D`/`E`) and the trace shows `"verdict": "approved"` anyway.
     `prompt_ui.console_prompt()` only ever explicitly checked `choice == "d"` and `choice == "e"` —
     literally any other input, including a blank Enter, silently fell through to a bare `# default / "a"`
     comment and was treated as approved. This is the least safe possible default for a gate whose entire
     purpose is deliberate human approval — the whole risk_classifier.py/boundary_guard.py safety model
     assumes this gate only ever approves on a genuine, intentional approval. Fixed by rewriting the
     function as a loop that re-prompts on anything not recognized as approve/deny/edit (accepting both
     the single-letter and full-word forms), never falling through to approval by default. Confirmed the
     GUI's `confirmation_dialog.py` never had this problem — it already defaults `self.verdict = "denied"`
     and only flips to approved via an explicit button click, so this bug was isolated to the CLI path.
  2. **The typed test message landed in the terminal, not Notepad.** The terminal transcript shows `This
     is a test message.` printed after the script had already exited — the text was typed into whatever
     window still had OS keyboard focus at that moment, not into Notepad. Root cause:
     `mouse_keyboard.py`'s `type_text()` called `pyautogui.typewrite()` completely blindly, with no
     verification that the intended window actually had focus, and `click_at()` had no settle delay for a
     newly-launched app (Notepad) to actually finish opening before the very next step tried to type.
     Fixed with an actual focus check, not a guess: `type_text()` now accepts an optional
     `expect_window_contains` argument and polls the real active window title (via a new
     `get_active_window_title()` on the `OSController` protocol, wrapping `pyautogui.getActiveWindow()`)
     until it matches, up to a timeout, raising `RuntimeError` instead of typing into the wrong window if
     it never does. `action_router.py`'s desktop `type` handler passes `params.get("expect_window_contains")`
     through, and `SYSTEM_PROMPT` now tells the planner to supply it whenever a type step is meant for a
     specific just-opened app (e.g. `{"text": "...", "expect_window_contains": "Notepad"}`). Also added a
     brief post-click settle delay in `click_at()`/`double_click_at()` as a cheap, harmless floor
     underneath the real fix (some UI transitions, like a menu opening, have no distinct window title to
     poll for).
- **Why:** Exactly what Phase 7 exists to surface, continuing the same pattern as every other entry today
  — real bugs invisible to any mock, found only because the user ran real tasks on real hardware. The gate
  bug in particular is a genuine safety-relevant finding: the entire confirmation-gate design assumes
  approval is always deliberate, and this proves that assumption had a real hole in the one place a human
  actually interacts with it.
- **Impacts:** 249 → 258 tests passing (+9: 4 `test_prompt_ui.py` covering unrecognized-input re-prompt,
  re-prompt-then-deny, blank-input-not-implicit-approve, and full-word accept; 4 `test_mouse_keyboard.py`
  covering unverified-default behavior, wait-then-type success, case-insensitive matching, and
  raise-instead-of-type-into-wrong-window with an explicit assertion that `typewrite()` is never called in
  the failure case; 1 `test_action_router.py` confirming `expect_window_contains` passes through). Phase
  7's success criterion is now substantially met for both execution paths — one full task has completed
  end-to-end on real Windows hardware via both browser and desktop routes, with two more real,
  previously-unknown bugs found and fixed as a direct result. Not yet done: the user has not re-run the
  desktop task again against these two newest fixes to confirm the test message now actually lands inside
  Notepad; DPI/multi-monitor scaling also remains unverified in any run so far.

### [2026-08-01] Episodic replay was silently resurrecting pre-fix bugs + window re-activation +
  auto-approve flag (user request)
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/memory/episodic_store.py`, `src/action/mouse_keyboard.py`,
  `src/confirmation/gate.py`, `src/config.py`, `src/main.py`, `.env.example`,
  `tests/memory/test_episodic_store.py`, `tests/action/test_mouse_keyboard.py`,
  `tests/confirmation/test_gate.py`, `tests/test_config.py`.
- **What changed:**
  1. **Root cause of the previous entry's fix appearing not to work: episodic replay bypasses the
     planner entirely, including any prompt/schema fix made to it.** The user re-ran the exact same
     desktop task and the test message landed in the terminal again, despite the `expect_window_contains`
     fix from the immediately preceding entry. The trace showed why: `"llm_call": false` on every step,
     and `"status": "replay_attempt", "source_episode_id": 6, "match_score": 1.0"` — `EpisodicStore.
     find_match()` matched the new instruction against an episode recorded during the FIRST (pre-fix)
     desktop run, and replayed its stored steps verbatim, including a step-4 `params` dict with no
     `expect_window_contains` key at all, because that field didn't exist yet when episode 6 was
     recorded. The planner (and its fixed prompt) never ran at all for this task. This is a durable,
     general problem: any future safety-relevant change to the step schema can be silently undone by
     replay for as long as an old matching episode exists. Fixed with a `STEP_SCHEMA_VERSION` gate
     (currently 2, bumped from an implicit 1): every recorded episode is stamped with the schema version
     active when it was recorded, `find_match()` only ever offers episodes stamped with the CURRENT
     version as replay candidates, and a migration backfills pre-existing databases' rows as version 1 (correctly
     excluding them all from replay under version 2). Older episodes remain in the database for
     history/review purposes, just never replayed. Future changes with the same "old stored steps could
     miss a safety-relevant field" shape should bump this constant again.
  2. **Window re-activation, not just detection.** The `expect_window_contains` check from the previous
     entry only ever detected a focus mismatch and raised — it never tried to fix it. Given the user's
     description of the actual mechanism (approving in the terminal steals OS focus away from the real
     target app, which then sits in the background), `mouse_keyboard.py`'s `OSController` protocol gained
     `activate_window(title_keyword) -> bool` (wrapping `pyautogui.getWindowsWithTitle(...).activate()`),
     and `type_text()`'s polling loop now attempts activation exactly once on the first mismatch before
     continuing to poll — actively trying to reclaim focus for the intended window rather than only ever
     passively waiting and hoping.
  3. **`AUTO_APPROVE_EXTERNAL` (explicit user request).** The user asked for a flag that approves
     everything before even prompting, specifically because the act of approving in the terminal is itself
     what causes the target app to lose focus. Added `auto_approve_external` to `ConfirmationGate`: when
     enabled, External-risk steps are approved with `prompt_fn` never even called (not a fast default
     answer — the prompt never appears, so there's no approve-in-the-terminal focus-steal to begin with).
     Deliberately, unconditionally does NOT apply to `Risk.DESTRUCTIVE` regardless of this setting — that
     tier's typed-CONFIRM-phrase requirement remains this project's one genuinely non-negotiable
     human-in-the-loop gate, the same way `boundary_guard.py`'s hard boundaries can't be disabled by any
     config value. Wired through `config.py`'s `AUTO_APPROVE_EXTERNAL` env var (default `false`) and
     `main.py`, which prints a loud, explicit warning banner on startup whenever it's enabled, matching
     this project's convention for every other safety/behavior trade-off.
- **Why:** (1) is a direct root-cause investigation of why the previous entry's fix "didn't work" — it did
  work, it just never got the chance to run. (2) and (3) are direct responses to the user's own diagnosis
  and explicit request, implemented in the same defense-in-depth spirit as the rest of this project (fail
  loud rather than silently guess, never let a convenience feature erode the one non-negotiable gate).
- **Impacts:** 258 → 270 tests passing (+12: 4 `test_episodic_store.py` covering the exact real-world
  stale-replay scenario, current-version replay still working, and DB migration correctness; 3
  `test_mouse_keyboard.py` covering activation-attempted-once-on-mismatch, no-activation-when-already-
  focused, and activation-not-spammed-every-poll; 3 `test_gate.py` covering prompt-never-called when
  auto-approved, off-by-default, and the hard guarantee that Destructive is never affected; 2 additional
  `test_config.py` for the new env var, plus reusing the existing default/case-insensitivity pattern). Not
  yet done: the user has not yet re-run the desktop task against all of today's fixes together to confirm
  a clean end-to-end result with the stale episode now correctly excluded from replay.

### [2026-08-01] Chrome launch was blocking purely desktop-only tasks — made lazy; two GUI-path gaps found
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/action/playwright_driver.py`, `src/brain/orchestrator.py`,
  `src/gui/worker.py`, `tests/action/test_playwright_driver.py`, `tests/brain/test_orchestrator.py`.
- **What changed:**
  1. **Chrome now launches lazily, on first real browser use, not unconditionally at startup.** The user
     hit a fresh crash: `python -m src.main "open Notepad and type a test message"` — a task that never
     touches a browser at all — failed with `ChromeProfileLaunchError` before a single step ran, because
     `main.py`'s `with PlaywrightDriver(...) as driver:` wraps every task unconditionally, and the
     constructor launched Chrome immediately. Worse, `orchestrator._observe()` called
     `driver.current_url()`/`current_title()` on every step to build the planner's screen-state context —
     so even if construction were made lazy, the very first observation call would still force a launch,
     regardless of whether the task ever needed a browser. Fixed both halves together:
     `PlaywrightDriver`'s constructor now only stores its arguments; `_ensure_launched()` is called at the
     top of every real browser method (`navigate`/`click`/`type_text`/`scroll`/`screenshot`/`current_url`/
     `current_title`), and a new `is_launched` property reports whether that's happened yet.
     `orchestrator._observe()` now checks `is_launched` first and returns a `{"url": None, "title": None,
     "browser_launched": False}` placeholder instead of calling into the driver if Chrome hasn't launched
     — so a purely desktop-only task never touches Playwright/Chrome at any point in its lifecycle, and a
     Chrome launch failure can no longer block a task that was never going to use a browser in the first
     place. `_gate_context()`/`_capture_verification_screenshot()` were already safe (prefer
     `mouse_keyboard`'s OS-level screenshot, only fall back to the browser's), so no change was needed
     there.
  2. **Found while checking the GUI path for the same eager-launch issue: two of today's earlier fixes
     were only ever wired into `main.py`, never into `src/gui/worker.py`.** `worker.py` constructs its own
     `ConfirmationGate`/`OCREngine` independently of `main.py` (the CLI and GUI are separate entry points
     sharing the same core), and neither the `TESSERACT_CMD` fix nor the `AUTO_APPROVE_EXTERNAL` feature
     from earlier today had been ported over — meaning a user running via the GUI specifically would still
     hit the original Tesseract-not-on-PATH failure even after `python -m src.doctor` passed, and would
     have no access to the auto-approve flag at all. Fixed both: `worker.py` now passes
     `tesseract_cmd=self._cfg.tesseract_cmd` to `OCREngine` and `auto_approve_external=self._cfg.
     auto_approve_external` to `ConfirmationGate`, matching `main.py` exactly. Not independently
     live-tested (GUI tests require PySide6, unavailable in this build environment — see `docs/STATUS.md`'s
     standing note on this), but the change is a direct, minimal port of an already-tested pattern.
- **Why:** Direct fix for the user's live crash, plus the general architectural principle it exposes: a
  task's dependencies should match what it actually does, not what the busiest possible task might need.
  The GUI-path gaps are a reminder that this project has two independent entry points sharing core logic,
  and a fix made in one isn't automatically present in the other — worth spot-checking both whenever a
  similar cross-cutting config wiring fix is made in the future.
- **Impacts:** 270 → 277 tests passing (+7: `test_playwright_driver.py` fully rewritten for lazy-launch
  semantics with new coverage for constructor-never-launches, `is_launched` before/after, `profile_name`
  never forcing a launch, safe no-op `close()` before any launch, and launch-only-attempted-once across
  multiple calls; 1 new `test_orchestrator.py` test proving a desktop-only task's `_observe()` calls never
  reach `driver.current_url()`/`current_title()` when unlaunched). Not yet done: the user has not yet
  re-run the desktop task against this fix to confirm it no longer depends on Chrome at all; the GUI-path
  fixes in `worker.py` have not been live-verified in either build environment.
