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
