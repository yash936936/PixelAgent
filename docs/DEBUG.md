# Debug Protocol

Run this full pass every time the codebase is updated — not just before a release. Never hand off code that
hasn't been through this pass.

## Prompt/instructions for the AI

```
You are performing a full debug pass on the pixel-agent codebase after a code update.
Go file by file, in the order listed in docs/STATUS.md. For EACH file:

1. READ the full file, not a summary or a diff — line by line.
2. Check for:
   - Broken logic (does the code do what its description in PHASES.md says it should?)
   - Syntax errors / would this file fail to import or compile?
   - Missing dependencies (is everything it imports declared in requirements.txt?)
   - Missing files (does it reference another file/module that doesn't exist yet, or a path that
     isn't created by any phase in PHASES.md?)
   - Dead/unreachable code paths
   - Silent failure points (bare except, swallowed errors, unchecked return values)
   - Any place a hard boundary from TRD.md §6 could be bypassed (this check is non-negotiable —
     flag it even if it looks like an edge case)
   - Any place risk classification (TRD.md §5) could be skipped or misapplied
3. ACTUALLY RUN what can be run: import the module, run its unit tests if present, run the
   relevant part of the app end to end for at least one happy-path case.
4. For every issue found: fix it, then re-run step 3 to confirm the fix worked.
5. Record every issue found and fixed in a "Debug Notes" entry (see format below) — do not fix
   silently and move on without a record.
6. After all files pass, update docs/STATUS.md and add a docs/DECISIONS.md entry summarizing the
   debug pass.

Do not skip a file because it "looks right." Do not stop at the first error in a file — finish
checking that file completely, then move to fixes.
```

## Debug Notes entry format
Append to the bottom of this file after each pass:

```
### [YYYY-MM-DD] Debug pass — <scope, e.g. "Phase 1 complete">
- Files checked: <list, or "all">
- Issues found:
  1. `path/to/file.py` — <issue> — <fix applied>
  2. ...
- Issues NOT fixed (external blockers, e.g. missing real API key): <list, or "none">
- Tests run: <command(s)>
- Result: <pass/fail + brief>
```

## Special checks by subsystem
- **`brain/risk_classifier.py`**: every entry in the `TRD.md §5` table must have at least one test case;
  verify no action type falls through to an implicit "Local" default.
- **`confirmation/gate.py`**: verify it's structurally impossible for an External/Destructive step to reach
  `action_router.py` without a resolved approval — trace the call path, don't just read the function.
- **`action/action_router.py`**: verify routing logic actually prefers Playwright for web targets before
  falling back to pixel control, per `TRD.md §3.4`.
- **`memory/episodic_store.py`**: verify a failed replay correctly falls back to fresh planning rather than
  silently repeating a broken plan.

---

## Debug Notes log

### [2026-07-11] Debug pass — Phase 1 complete
- Files checked: all 12 `src/` files created in Phase 1 (`config.py`, `brain/risk_classifier.py`,
  `brain/planner.py`, `brain/orchestrator.py`, `action/playwright_driver.py`, `action/action_router.py`,
  `confirmation/gate.py`, `confirmation/prompt_ui.py`, `observability/logger.py`, `main.py`) plus 3 test
  files.
- Issues found:
  1. `brain/orchestrator.py` — originally called `PlaywrightDriver` methods directly in `_execute()`,
     bypassing `ActionRouter` entirely (contradicted `TRD.md §3.4`'s routing requirement and would have
     made Phase 2's desktop-control branch require rewriting `orchestrator.py` instead of just
     `action_router.py`) — fixed by adding an `ActionRouter` param to `Orchestrator.__init__` and routing
     `_execute()` through it.
  2. `confirmation/gate.py` — initial version would have let a Destructive step through as approved even
     without the re-typed "CONFIRM" phrase if the prompt callable itself said "approved" — fixed by adding
     an explicit phrase check inside `request_approval()` so this can't be bypassed by a buggy or malicious
     `prompt_fn` implementation; added `test_destructive_requires_confirm_phrase` to lock this in.
  3. `action/action_router.py` importing `playwright_driver.py` required the `playwright` pip package to be
     installed even for router unit tests that mock the driver — confirmed intentional (import-time
     dependency), not a bug, but noted here since it's a real environment requirement, not just a "nice to
     have."
- Issues NOT fixed (external blockers): live end-to-end run against a real Chrome profile and real
  `ANTHROPIC_API_KEY` — requires `playwright install chromium` and real credentials, which live on the
  user's machine, not this build environment.
- Tests run: `pip install -r requirements.txt` (partial — chromium browser binary not installed, not needed
  for unit tests); `python -m pytest tests/ -v` — 16/16 passed; `python -c "import ..."` smoke-import of
  every Phase 1 module — all imported cleanly.
- Result: **Pass** for everything testable in this environment. Live browser + real LLM call still needs to
  be verified by the user before calling Phase 1 fully done per `PHASES.md`'s success criterion.

### [2026-07-11] Debug pass — Anthropic to Gemini swap
- Files checked: `requirements.txt`, `.env.example`, `src/config.py`, `src/brain/planner.py`, `src/main.py`
- Issues found:
  1. First implementation used `google-generativeai` (the deprecated package) — surfaced as a
     `FutureWarning` during the re-verification import check, not a silent issue. Fixed by switching to the
     current `google-genai` package (`google.genai.Client` + `google.genai.types.GenerateContentConfig`)
     and updating `requirements.txt` accordingly.
- Issues NOT fixed (external blockers): live call to the real Gemini API not verified in this environment —
  needs a real `GEMINI_API_KEY` on the user's machine.
- Tests run: `python -c "import ..."` clean-import check (no warnings) on all touched modules;
  `python -m pytest tests/ -q` — 16/16 passed (unaffected by the LLM backend swap since tests mock/avoid the
  planner's network call).
- Result: **Pass.**

### [2026-07-11] Debug pass — Phase 2 complete
- Files checked: `src/perception/ocr.py`, `src/perception/element_detector.py`,
  `src/perception/screen_diff.py`, `src/action/mouse_keyboard.py`, `src/action/action_router.py` (desktop
  branch), `src/brain/replanner.py`, `src/brain/orchestrator.py` (verify/replan loop), `src/main.py`
  (updated wiring).
- Issues found:
  1. `orchestrator.py`'s first draft called `PlaywrightDriver` for verification screenshots only, which
     meant desktop-only tasks (no browser involved) would never get verified — fixed by preferring
     `MouseKeyboard.screenshot()` first (covers both web and desktop since it captures the whole screen),
     falling back to the browser screenshot only if no `MouseKeyboard` is configured.
  2. `_execute_and_verify`'s recursive retry did not cap total recursion depth independently of
     `Replanner.max_retries` — confirmed this is safe because `Replanner.correct()` itself raises
     `ReplanExhausted` once `attempt > max_retries`, so recursion in `orchestrator.py` is bounded by that,
     not by orchestrator code; added `test_max_steps_exceeded_raises` and
     `test_replan_triggered_on_screen_mismatch` to lock in both the replan path and the step-budget path.
  3. `ActionRouter._resolve_coords` originally didn't distinguish "no OCR engine configured" from "OCR
     found nothing" — both would have raised the same generic error, making it hard to tell a config problem
     from a genuine "element not on screen" case. Fixed by raising `UnsupportedTargetType` for the former and
     a plain `ValueError` for the latter; added separate tests for each.
- Issues NOT fixed (external blockers): live OCR against a real screenshot (needs the Tesseract binary
  installed, not just the `pytesseract` Python wrapper) and live mouse/keyboard control (needs a real
  display) — both require the user's actual Windows machine, not this build environment.
- Tests run: `python -c "import ..."` clean-import check on all Phase 2 modules — no errors; `python -m
  pytest tests/ -v` — 51/51 passed (16 Phase 1 + 35 Phase 2, including the new `test_orchestrator.py`
  integration-style tests that exercise the gate/verify/replan wiring together, not just each module in
  isolation).
- Result: **Pass** for everything testable in this environment. Live screen/OCR/mouse control still needs
  to be verified by the user on Windows before calling Phase 2 fully done per `PHASES.md`'s success
  criterion.

### [2026-07-11] Phase 5 debug pass — risk_classifier.py expansion + trace_replay.py
- Files reviewed line-by-line: `src/brain/risk_classifier.py` (full rewrite of keyword tables + new guard
  logic), `src/observability/trace_replay.py` (new).
- Issues found and fixed during this pass:
  1. First draft of the expanded External keyword list included bare `"review"` and `"rate"` — both would
     have false-positived on extremely common read-only/benign phrasing (e.g. "review the document",
     "rate limit"). Replaced with narrower, intent-specific phrases (`"submit review"`, `"write a review"`,
     `"leave a rating"`) that don't collide with ordinary text.
  2. The read-only-guard (`_READ_ONLY_GUARDS`) needed a second check (`_has_actual_verb`) so a sentence
     like "check if the delete button works, then click delete" doesn't get incorrectly downgraded just
     because it also contains a guard phrase — added a test (`test_read_only_guard_does_not_suppress_real_click`)
     to lock this in, alongside the base case
     (`test_read_only_check_for_delete_button_not_escalated`).
  3. `trace_replay.py`'s `screenshot_path` originally only checked `step["screenshot"]`; `outcome` payloads
     from `action_router.py`/`perception` can also carry a screenshot reference, so both containers are now
     checked. Verified with `test_screenshots_deduplicated_in_order` using a screenshot recorded on
     `outcome` only.
  4. `TraceReplay.load()` initially let malformed JSON lines pass through as skipped rows — changed to
     raise `TraceLoadError` immediately (per docs/DEBUG.md's general principle of failing loud), since a
     silently-incomplete trace is worse than a load failure the developer can see.
- Issues NOT fixed (out of scope / external blockers): the expanded keyword tables are still static/rule-
  based and can't yet be validated against genuine Phase 1-4 usage logs, since no live run has happened
  outside this build environment (same blocker noted throughout Phases 2-4). Real-log validation is the
  Phase 5 follow-up noted in `docs/STATUS.md`'s Next action.
- Tests run: `python -m pytest tests/ -v` — 121/121 passed (97 pre-existing Phase 1-4 tests, unmodified and
  still green, + 24 new: 11 in `test_risk_classifier.py`, 13 in the new `test_trace_replay.py`). Also ran
  `python -m src.observability.trace_replay <demo_log_dir>` manually against a hand-built sample
  `.jsonl` trace to confirm the CLI path (not just the unit tests) produces correct step/gate/event/
  task_complete summary lines end to end.
- Result: **Pass** for everything testable in this environment. Phase 5's "no unclassified/misclassified
  risk cases observed in a full regression pass over logged tasks" criterion still needs a real corpus of
  logged tasks from live use to fully verify — `unclassified_or_missing_risk()` on `TraceReplay` is the
  tool for the user to run that check once such logs exist.
### [2026-07-12] Gap-remediation debug pass
- Files reviewed and modified: `boundary_guard.py` (new), `risk_llm_judge.py` (new),
  `risk_classifier.py`, `orchestrator.py`, `planner.py`, `gate.py`, `prompt_ui.py`,
  `playwright_driver.py`, `logger.py`, `episodic_store.py`, `main.py`, `requirements.txt`.
- Issues found and fixed during this pass (beyond the ones described in `docs/DECISIONS.md`'s entry for
  the same date):
  1. First implementation of `_check_boundary()`/`_classify_risk()` insertion into `orchestrator.py`
     accidentally clobbered the body of the pre-existing `_observe()` method via an imprecise
     `str_replace` — caught immediately by the full test suite (`AttributeError: 'Orchestrator' object
     has no attribute '_observe'`), fixed by restoring the method body.
  2. `BoundaryBlocked` was originally only caught inside `_execute_and_verify`'s try/except, but
     `_check_boundary()` is actually called *before* that try block (ahead of gating) — the exception
     would have propagated uncaught and crashed the task instead of cleanly halting it. Moved the
     try/except to wrap the actual call site.
  3. `_capture_verification_screenshot()`'s new logging of "verification_unavailable" was initially
     unconditional, which would have spammed an event into every single step's trace even in
     Phase-1-only configurations with no replanner configured (i.e., verification intentionally not
     requested). Gated screenshot capture (and therefore its logging) behind `self._replanner is not
     None`, matching the existing `_can_verify` gating logic.
  4. A test boundary-guard phrase ("bypass the verification check") matched two categories
     simultaneously by coincidence, making the test's assertion of a single expected `Boundary` value
     fragile; reworded to an unambiguous phrase from the intended category only.
  5. First draft of `HostedLLMPlanner._generate_fn` duplicated the request-building logic already in
     `next_step()` slightly differently; confirmed via test that both paths produce identical Gemini API
     calls before finalizing, to avoid two subtly different code paths hitting the same API.
- Tests run: `python -m pytest -q` — 165/165 passed (121 pre-existing, unmodified in behavior, + 44 new:
  boundary guard 7, LLM risk-judge 6, orchestrator wiring 3, gate context 3, prompt_ui 4, logger
  redaction 7, planner cost 4, main.py wiring 2, episodic match_score 2, risk_classifier confidence 3,
  plus incidental additions).
- Result: **Pass.** Every concretely-identified, code-level gap from the review has either been fixed
  and tested, or is called out explicitly in `docs/STATUS.md`'s Known Gaps section as something this
  remediation pass could not fully close (see that section for the honest remainder — mainly things that
  require a live environment, a product-level redesign, or are fundamentally unbounded, like a
  keyword-based boundary guard's exposure to sufficiently novel phrasing).
