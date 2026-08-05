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
### [2026-07-12] Track B eval-harness build + bug caught on first run
- Files reviewed/modified: `risk_model_backend.py` (new), `planner.py` (rename), `config.py`, `main.py`,
  `eval/adversarial_boundary_eval.py` (new), `eval/adversarial_cases.jsonl` (new), `risk_classifier.py`,
  `training/*` (new).
- Issues found and fixed during this pass:
  1. **Real bug, caught by the eval harness on its very first run, not by unit tests.** The read-only
     guard's `_has_actual_verb()` checked the combined `"{step['action']} {step['description']}"` text
     for a preceding action verb (`click`/`press`/`tap`/`hit`/`select`). Since `step['action']` is itself
     almost always one of those verbs (e.g. `"click"`), and it's always prepended first, the check
     trivially passed for every `action="click"` step regardless of description — silently defeating the
     read-only guard for the single most common action type. Existing unit tests didn't catch this
     because they all happened to construct cases where the description's own wording lined up with the
     desired result by coincidence. Fixed by checking `step['description']` alone.
  2. That fix introduced a second, narrower bug the harness caught on the very next run: case `adv_021`
     ("check if the delete button works, then click delete") regressed to `local`, because
     `_has_actual_verb()` used `text.find(keyword)` (first occurrence only) — "delete" appears twice in
     that description, and the first occurrence ("delete button") has no preceding verb, so the function
     returned `False` and never checked the second occurrence ("click delete"). Fixed by scanning every
     occurrence of the keyword in the description, not just the first.
  3. Confirmed the eval harness's `_predict_with_model()` path (keyword + optional model layer) exactly
     mirrors `orchestrator.py`'s real `_classify_risk()` logic line-for-line, including the
     boundary-guard-first ordering and the escalate-only constraint — added
     `test_model_layer_never_overrides_a_boundary_violation` and
     `test_model_layer_never_downgrades_a_confident_keyword_match` specifically to lock this in, since a
     harness that scores a different code path than production would give a false sense of security.
  4. Adjusted two adversarial dataset entries (`adv_023` "cancel my subscription", `adv_024` "empty out
     the recycle bin") after discovering they were meant to test evasive phrasing but happened to expose
     a separate, smaller keyword-substring-matching gap (an inserted word breaking the exact-phrase
     match) rather than genuine semantic evasion — kept them in the dataset as legitimate baseline gaps,
     documented explicitly in `eval/README.md`'s "Known baseline gaps" section rather than either quietly
     fixing them with a keyword patch (re-entering the unbounded-list problem) or silently dropping them.
- Tests run: `python -m pytest -q` — 189/189 passed (165 pre-existing, unmodified in behavior, + 24 new:
  risk_model_backend 6, eval harness 7, prepare_dataset 5, train_lora 3, test_main.py rewritten 4 tests
  for the new config-driven builder). Also ran
  `python -m eval.adversarial_boundary_eval` directly (not just via pytest) to confirm the CLI report
  output is readable and correctly flags per-category recall, and
  `python -m training.prepare_dataset --target risk_model/--target planner` to confirm both actually run
  end-to-end and report honestly on the current (near-empty) real-data situation rather than silently
  producing something that looks more complete than it is.
- Result: **Pass.** The harness itself is now real, tested, and already proved its worth by catching two
  genuine bugs before any trained model was ever involved. The keyword-only baseline's actual eval score
  (~40% overall, low per-category recall on the two highest-stakes categories) is recorded honestly in
  `eval/README.md` as the justification for Track B's risk model, not something to chase to 100% with
  more keywords.

### [2026-07-12] Debug pass — Track B adoption verification (this session)
- Files checked: entire project, verified fresh rather than trusting prior session's own claims.
- Actions taken: clean venv, exact pinned `pip install -r requirements.txt` (succeeded), `pip install
  pytest` (dev-only, correctly not in `requirements.txt`), `python -m pytest tests/ -q` (189/189 passed),
  a full `pkgutil.walk_packages` smoke-import of all 29 `src/` modules (0 errors), and a real run of
  `python -m eval.adversarial_boundary_eval` (reproduced the documented ~40% overall / 14%
  evasive-category baseline accuracy exactly).
- Issues found: none — this pass was purely verification of an already-debugged prior state, not new
  development.
- Result: **Pass.** Confirms the project's own prior `DECISIONS.md`/`STATUS.md` claims are accurate, not
  just internally consistent.

### [2026-07-12] Debug pass — GUI implementation (this session)
- Files checked: all 10 new `src/gui/` files, plus the 2 modified `src/memory/` files
  (`semantic_store.py`, `memory_api.py`).
- Issues found:
  1. `src/gui/style.py` — `SPACING` dict was keyed by string (`"24"`) instead of int, so
     `style.SPACING[24]` (used throughout the widget files) raised `KeyError`. Caught immediately by a
     direct smoke-test, before any widget code ran. Fixed by casting keys to `int` at load time.
  2. `src/gui/widgets/memory_panel.py` — initially reached into `MemoryAPI._semantic` (private attribute)
     to list preferences, violating `memory_api.py`'s own documented boundary. Fixed by adding a public
     `all_preferences()` method to `SemanticStore` and a facade on `MemoryAPI`; added
     `test_all_preferences_returns_reserved_namespace_only` and `test_all_preferences_facade` to lock this
     in at both layers.
  3. `src/gui/widgets/confirmation_dialog.py` — `_on_approve()` used `self._edit_box.isVisible()` to
     detect whether the user had opened the edit field. This is a real Qt semantics bug: `isVisible()`
     reflects whether the widget is actually painted on screen, which depends on the top-level window
     having been shown — it does *not* simply reflect the last `setVisible()` call. Caught by
     `tests/gui/test_confirmation_dialog.py::test_edit_box_populates_edited_step_when_visible` failing on
     first run (the edit text was silently dropped). Fixed with an explicit `_edit_mode` boolean instead
     of relying on Qt's visibility state — this is the kind of "silent failure point" this very protocol
     exists to catch, and it would have shipped invisibly since it only manifests as "my edit never took
     effect," not a crash.
  4. Traced the `GateBridge`/`Qt.BlockingQueuedConnection` mechanism specifically for a deadlock risk,
     since the wrong Qt connection type here (e.g. `AutoConnection` resolving to `QueuedConnection` across
     threads) would hang the entire app on the first External/Destructive step with no error message at
     all — the worst possible failure mode for a safety-critical gate. Verified with a real `QThread` (not
     a mock) in `tests/gui/test_gate_bridge.py::test_gate_bridge_round_trip_across_real_thread`, which
     would hang and eventually be killed by `worker.wait(2000)` timing out if the connection type were
     wrong, rather than silently reporting false success.
- Issues NOT fixed (external blockers): the GUI has never been shown on a real display (only
  `QT_QPA_PLATFORM=offscreen`, which exercises real Qt widget code but not actual rendering/window-manager
  interaction) and never driven through a real live task run — both require the user's actual Windows
  machine.
- Tests run: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q` — 227/227 passed (189 pre-existing +
  38 new); a full `pkgutil.walk_packages` smoke-import of all 41 `src/` modules including `src.gui` and
  its `widgets` subpackage — 0 errors.
- Result: **Pass** for everything testable without a real display. Live rendering and a real end-to-end
  task run through the GUI still need to be verified by the user on Windows.

### [2026-07-13] Debug pass — first live run bug fix (profile launch)
- Files checked: `src/action/playwright_driver.py`, `src/gui/widgets/stats_panel.py`
- Issues found:
  1. **The project's first bug ever caught by a real live run, not a unit test.** The user ran a real
     task through the GUI; the screenshots showed Pixel opening Gmail's logged-out marketing page and
     needing a manual "Sign in" click, instead of the user's actual, already-authenticated inbox. Root
     cause: `PlaywrightDriver` concatenated `profiles_dir / profile_name` and handed the result to
     Chromium as if it were a complete, standalone user-data directory — Chromium creates an empty
     `Default` profile inside whatever directory it's given if one doesn't already exist there, so this
     silently produced a brand-new blank profile every run instead of reusing the real one. No prior unit
     test caught this because none exercised the actual `launch_persistent_context` call — it had only
     ever been mocked at the `ActionRouter`/`Orchestrator` level, one layer too high to see this. Fixed by
     switching to `--profile-directory=<name>` against the real Chrome "User Data" root, and added
     `tests/action/test_playwright_driver.py` that mocks `sync_playwright` itself and asserts the exact
     `user_data_dir`/`args` passed to `launch_persistent_context` — this is now the regression test for
     this specific class of bug.
- Issues NOT fixed (external blockers): whether "Profile 3" is actually the user's intended "Yash" profile
  on disk is still something only the user can confirm via `chrome://version` — the code fix makes profile
  selection *work correctly*, it doesn't know which profile name is the right one.
- Tests run: fresh venv, `pip install -r requirements.txt -r requirements-gui.txt pytest`,
  `QT_QPA_PLATFORM=offscreen python -m pytest -q` — 232/232 passed (227 previous + 5 new); full
  `pkgutil.walk_packages` smoke-import of all 41 `src/` modules — 0 errors.
- Result: **Pass.** This entry exists specifically because a live run found something 232 passing unit
  tests could not — worth keeping as a concrete example in this protocol of why "all tests green" isn't
  the same as "verified against the real external system."

### [2026-08-01] Debug pass — real-pixel integration harness finds a genuine OCR bug on first run
- Files checked: `src/perception/ocr.py`, `src/perception/element_detector.py`, `src/perception/screen_diff.py`,
  plus new `tests/integration/` fixtures and tests.
- Issues found:
  1. **A real bug, found by the new offline real-pixel harness (`tests/integration/`), not a live Windows
     run.** `test_real_ocr_pipeline.py` — real headless Chromium render, real screenshot, real Tesseract —
     failed immediately: Tesseract returned zero words on a standard solid-blue "Submit" button with white
     text, finding only the plain black-on-white "Username:" label next to it. Every prior test in this
     project exercised `OCREngine` against hand-built `OCRWord` lists, so this exact failure mode had never
     been triggered before. Isolated the cause by cropping just the button out of the screenshot and testing
     it alone: an inverted, upscaled copy of the *same crop* still failed identically, which ruled out
     color-contrast and resolution as the cause. Root cause: Tesseract's `textord` layout-analysis pass,
     which decides what regions are worth reading before OCR even runs, treats a large solid-color rectangle
     as a non-text "picture" block and discards it — a heuristic tuned for scanned documents that misfires on
     ordinary UI elements (solid buttons, colored panels, dark-mode surfaces) regardless of what's drawn on
     them. Fixed with `-c textord_min_linesize=1.0` passed to every `pytesseract.image_to_data` call in
     `ocr.py` — verified this alone finds both the label and the button text, at original resolution, default
     page-segmentation mode, no other changes needed. Added
     `tests/perception/test_ocr_solid_background_regression.py`, a fast mock-free test against a small
     synthetically-drawn solid-button image, so this specific regression can never silently return without a
     visible test failure — it doesn't require Playwright/Chromium, unlike the fuller integration tier that
     originally found it.
  2. Also added, alongside the fix: `test_real_click_that_changes_the_page_is_detected` (true-positive check
     that a real, large visible UI change is correctly flagged by `screen_diff.compare()`) and
     `test_real_blinking_cursor_animation_false_positive_risk` (characterizes, rather than assumes, the false-
     positive risk of a small CSS blink animation — measured `change_ratio≈0.00009` against the default 0.01
     threshold, well clear of it; printed rather than silently asserted, so a human reviewer can see the
     actual number if the threshold is ever revisited for text-entry-heavy screens).
- Issues NOT fixed (external blockers, unchanged): real OS-level mouse/keyboard control, real DPI/multi-
  monitor scaling behavior, and a real Gemini API call all still require the user's actual Windows machine —
  this harness only closes the perception-pipeline half of "zero live validation," not the full end-to-end
  claim.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 221/221 passed (213 previous + 6 new real-pixel
  integration tests + 2 new OCR regression tests); `python -m eval.adversarial_boundary_eval --model
  semantic` — 73% overall (see `eval/README.md`'s 2026-08-01 update for the full per-category breakdown).
- Result: **Pass**, with one real, previously-undiscovered bug found and fixed as a direct result of this
  pass's own harness — the second time in this project's history (after the 2026-07-13 profile-launch bug)
  that testing against something more real than a mock has surfaced a bug unit tests alone could not.

### [2026-08-01] Debug pass — first real live task runs surface two real bugs (third and fourth times a
  real environment found what mocks couldn't)
- Files checked: `src/brain/planner.py`, `src/action/action_router.py`, plus the two real trace logs the
  user provided from their own Windows machine.
- Issues found:
  1. **Unhandled crash on a truncated Gemini response.** First browser task run ended in a raw Python
     traceback (`json.decoder.JSONDecodeError` inside `_parse_step`, propagating out of
     `HostedLLMPlanner.next_step()` uncaught). The response text was cut off mid-JSON
     (`'{\n  "action": "navigate", ... "url": "https://www.bing.com/search?q=weather"}'` — missing closing
     braces). Re-running the identical command by hand succeeded on the very next attempt, which is the
     key evidence this was transient generation variance rather than a reproducible bug a retry would just
     repeat. Fixed with a bounded (exactly one) retry in `next_step()` for both `HostedLLMPlanner` and
     `LocalFineTunedPlanner` — logs a warning and tries again once before raising, so a single bad
     generation no longer takes down the whole task.
  2. **First-ever desktop click failed immediately.** Trace log showed the confirmation gate correctly
     firing and being approved (`verdict: "approved"`, screenshot captured) — proof the GUI/gate machinery
     itself worked correctly on real hardware — but the actual click then failed:
     `"Desktop click step needs either explicit 'x'/'y' params or a 'target_text' keyword..."` because the
     planner had used `params={"selector": "Start button"}`, the web-schema key, on a `target_type=
     "desktop"` step. Root-caused to `SYSTEM_PROMPT` never actually distinguishing the two target types'
     param shapes in its example. Fixed both the prompt (explicit, separated web/desktop schema
     description) and, as defense-in-depth since prompt compliance is never guaranteed, a fallback in
     `action_router.py._resolve_coords()` treating a stray `selector` key as `target_text` on desktop
     steps.
- Issues NOT fixed / still open: the user has not yet re-run the desktop task against these fixes to
  confirm a full task completes end-to-end — the original run's final status was still `error`. DPI/
  multi-monitor scaling (flagged as untested since the `tests/integration/` harness fixed its viewport)
  remains unverified; this run happened to succeed on click resolution before the schema bug stopped it,
  so scaling accuracy specifically is still an open question for the next attempt.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 249/249 passed (244 previous + 3 planner-retry
  tests + 2 action-router-fallback tests).
- Result: **Partial pass.** Both bugs found this pass are fixed and covered by new tests, but Phase 7's own
  success criterion (one full task completing end-to-end on real hardware via each execution path) is not
  yet confirmed for the desktop path — that requires the user to re-run it against these fixes. This is
  the third and fourth time in this project's history (after 2026-07-13's profile bug and 2026-08-01's OCR
  `textord_min_linesize` bug) that something more real than a mock — here, an actual live run on the user's
  own machine — found a bug no test suite had.

### [2026-08-01] Debug pass — first fully-completed desktop task, two more real bugs (fifth and sixth)
- Files checked: `src/confirmation/prompt_ui.py`, `src/action/mouse_keyboard.py`,
  `src/action/action_router.py`, plus the trace log and terminal transcript from the user's own re-run.
- Issues found:
  1. **Safety-relevant: the CLI confirmation gate silently approved a typo.** The user typed `Notepad` at
     an approve/deny/edit prompt — not a recognized option — and the trace recorded `"verdict":
     "approved"` regardless. `console_prompt()` had no `else` branch; anything that wasn't exactly `"d"` or
     `"e"` fell through to an unlabeled default-approve. Confirmed this was NOT present in the GUI's
     `confirmation_dialog.py` (which already defaults to denied and only flips on an explicit button
     click) — isolated to the CLI path only. Fixed by looping until a real approve/deny/edit answer is
     given, never defaulting to approval on anything unrecognized, including a blank Enter.
  2. **The typed message went into the terminal, not Notepad.** Terminal transcript showed `This is a test
     message.` printed after the process had exited — proof the final `type` step's keystrokes landed
     somewhere other than the intended Notepad window. `mouse_keyboard.py`'s `type_text()` had no
     mechanism at all to check what currently had OS keyboard focus; it just called
     `pyautogui.typewrite()` and trusted the target was correct. Given the click-then-type steps ran back
     to back with no wait for Notepad to actually finish launching, the keystrokes almost certainly raced
     ahead of the new window gaining focus. Fixed with an actual verification, not a delay-and-hope: an
     optional `expect_window_contains` argument that polls the real active window title before typing and
     raises rather than typing blindly if the expected window never gains focus — plus a small settle
     delay after clicks as a secondary, low-cost safeguard.
- Issues NOT fixed / still open: the user has not yet re-run the desktop task against these two newest
  fixes to directly confirm the test message now lands inside Notepad (rather than just confirming the new
  code paths are individually unit-tested); DPI/multi-monitor scaling on click coordinates remains
  completely unverified in any run to date.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 258/258 passed (249 previous + 4 prompt_ui + 4
  mouse_keyboard + 1 action_router).
- Result: **Pass**, with two more real bugs found and fixed — one of them (the gate accepting invalid
  input as approval) a genuine safety-relevant finding, not just a functional one. This is the fifth and
  sixth time in this project's history that testing against something more real than a mock — here, the
  user's own live re-run — has surfaced a bug no test suite had, following 2026-07-13's profile bug,
  2026-08-01's OCR `textord_min_linesize` bug, and the same day's planner-crash/schema-mismatch pair.

### [2026-08-01] Debug pass — "the fix didn't work" investigation: episodic replay was the actual cause
- Files checked: `src/memory/episodic_store.py`, `src/brain/orchestrator.py`'s replay path,
  `src/action/mouse_keyboard.py`, plus the user's second desktop-task trace log.
- Issue found: the user re-ran the identical desktop task after the previous entry's `expect_window_
  contains` fix, and the test message landed in the terminal again — same symptom as before the fix. Before
  assuming the fix itself was wrong, checked the trace log first: every step showed `"llm_call": false` and
  the log opened with `"status": "replay_attempt", "source_episode_id": 6, "match_score": 1.0"`. This
  confirmed the planner never ran at all for this task — `EpisodicStore.find_match()` matched the new
  instruction against episode 6 (recorded during the FIRST, pre-fix desktop run) and replayed its stored
  steps verbatim. Episode 6's step 4 had `params={"text": "This is a test message."}` with no
  `expect_window_contains` key, because that field didn't exist when it was recorded — so the fix's own
  check had nothing to check. The fix was correct; it just never got invoked. Root-caused and fixed with a
  `STEP_SCHEMA_VERSION` gate on replay (see `docs/DECISIONS.md`'s matching 2026-08-01 entry for the full
  mechanism) — this is a durable fix for the general class of problem, not just this one instance, since
  any future safety-relevant schema change would have hit the identical failure mode.
- Also addressed in the same pass, per the user's own diagnosis of the underlying mechanism (approving in
  a terminal steals focus from the real target app): added active window re-activation (not just detection)
  in `mouse_keyboard.py`, and an explicit `AUTO_APPROVE_EXTERNAL` opt-in flag that skips the External-risk
  prompt entirely — never applying to Destructive, which keeps its confirm-phrase requirement unconditionally.
- Issues NOT fixed / still open: the user has not yet re-run the desktop task against the combined set of
  today's fixes (stale-episode exclusion + window re-activation) to directly confirm a clean end-to-end
  result; DPI/multi-monitor scaling remains unverified in any run to date.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 270/270 passed (258 previous + 4 episodic-store +
  3 mouse_keyboard + 3 gate + 2 config tests).
- Result: **Pass.** This is a good illustration of a debugging discipline worth keeping in this log: when a
  fix appears not to have worked, check whether it actually ran before assuming it's wrong — here the fix
  was correct, the replay path had simply routed around it entirely.

### [2026-08-01] Debug pass — a desktop-only task was needlessly dependent on Chrome launching at all
- Files checked: `src/action/playwright_driver.py`, `src/brain/orchestrator.py`'s `_observe()`/
  `_gate_context()`, `src/main.py`, `src/gui/worker.py`.
- Issue found: the user's very next attempt at "open Notepad and type a test message" — a task with no
  browser step anywhere in it — failed before a single step executed, with a `ChromeProfileLaunchError`
  traceback. Traced to `main.py`'s `with PlaywrightDriver(...) as driver:` wrapping every task
  unconditionally, and the driver's constructor launching Chrome immediately regardless of whether the
  task would ever use it. Checked whether making construction lazy alone would be sufficient, and it would
  not have been: `orchestrator._observe()` calls `driver.current_url()`/`current_title()` on every step
  (to give the planner current screen context), which would immediately force a launch on the very first
  observation regardless of the task type. Fixed both together — see `docs/DECISIONS.md`'s matching entry
  for the full mechanism.
- While spot-checking whether the GUI's separate entry point (`src/gui/worker.py`) had the same eager-
  launch problem (it didn't need a separate fix, since it uses the same `PlaywrightDriver`/`Orchestrator`
  classes), found two unrelated but real gaps: `worker.py` constructs its own `OCREngine`/
  `ConfirmationGate` independently of `main.py`, and never received either the `TESSERACT_CMD` fix or the
  `AUTO_APPROVE_EXTERNAL` feature added earlier in this same session — both were only ever wired into
  `main.py`. Fixed by porting the identical wiring into `worker.py`.
- Issues NOT fixed / still open: the user has not yet re-run the desktop task against this fix to confirm
  it completes without ever touching Chrome; the `worker.py` port has not been live-tested in any
  environment (GUI tests require PySide6, unavailable here) — it's a direct, minimal port of an
  already-tested pattern, but that's not the same as having been run.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 277/277 passed (270 previous + 6
  `test_playwright_driver.py` rewritten/new + 1 new `test_orchestrator.py`).
- Result: **Pass**, plus a reminder worth generalizing: this project has two independent entry points
  (`main.py` CLI, `src/gui/worker.py` GUI) sharing core logic, and a fix applied to one is not automatically
  present in the other — worth a deliberate spot-check of both whenever a future cross-cutting config-
  wiring change is made, rather than assuming parity.

### [2026-08-01] Debug pass — Gemini 429 rate limit crashed the task; unrelated test-file structure slip
  caught by running the tests
- Files checked: `src/brain/planner.py`, plus the user's crash traceback.
- Issue found: `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED` — free-tier quota (5 requests/
  minute) exhausted mid-task, crashing with an unhandled traceback. Confirmed this exception type is
  distinct from the `ValueError` the existing parse-failure retry catches, so that fix never engaged.
  Fixed with a dedicated `_generate_with_rate_limit_retry()` — catches API errors specifically where
  `code == 429`, reads the server's own suggested `retryDelay` from the error body, backs off and retries
  up to 3 attempts, and re-raises immediately (no retry at all) for any non-429 API error.
- Also caught, while writing the new tests: an earlier edit today had accidentally swallowed a test
  function's `def` line during a `str_replace`, leaving the next test's setup code (a `class FakeResponse`
  block) orphaned inside the previous test rather than starting its own. Running the full test file
  surfaced this immediately as a structural break; fixed by restoring the missing `def
  test_hosted_planner_generate_fn_reusable_for_risk_judge(monkeypatch):` line. Worth noting as a reminder
  to always run the affected file's full test suite after any edit, not just the newly added tests in
  isolation — this slip wouldn't have been visible from the new tests passing alone.
- Issues NOT fixed / still open: the underlying quota limit itself isn't something code can fix — a user
  on this free tier who hits this often will need to slow down between tasks or move to a paid plan; the
  retry only rides out a single transient hit, it doesn't raise the ceiling.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 281/281 passed (277 previous + 4 new: rate-limit
  retry-then-succeed, exhausted-retries-still-raises, non-429-never-retried).
- Result: **Pass.**

### [2026-08-02] Debug pass — reviewing three trace logs together instead of reacting to one error
- Files checked: `src/action/action_router.py`, `src/brain/planner.py`'s `SYSTEM_PROMPT`,
  `src/action/mouse_keyboard.py`, plus three trace logs the user shared from separate live runs.
- Approach: rather than treating the third trace's error message as a new bug in isolation, first checked
  whether the `expect_window_contains` fix from the previous day was actually working — it was: the trace
  clearly shows it correctly detected VS Code had focus (the user was watching the trace log there) instead
  of Notepad, and refused to type into it. That ruled out the fix itself as broken and reframed the
  question as "why didn't it recover in time," not "is the check wrong."
- Issues found, by comparing all three traces side by side rather than just the failing one:
  1. All three traces needed a mid-task replan on the very first step (clicking Start). Checked
     `action_router.py` directly rather than assuming the capability didn't exist — it did: `hotkey` was
     already fully wired to `mouse_keyboard.press_hotkey()`. The actual gap was `SYSTEM_PROMPT` never
     telling the planner this option existed, so it always attempted the fragile OCR click first. Fixed by
     documenting `hotkey` and explicitly recommending it for the Start menu specifically.
  2. Re-examined why the window-activation fix (proven working in issue detection) still failed to recover:
     a single activation attempt fired once, early, is exactly the kind of check that can miss a window
     that doesn't exist yet on a cold app launch. Fixed with periodic retries across a longer timeout
     window instead of a one-shot attempt.
- Issues NOT fixed / still open: the second trace's distinct `"Could not locate an on-screen element
  matching 'Start'"` failure (after a replan re-attempted clicking Start when the Start menu had likely
  already closed) looks like a separate, more transient OCR/UI-timing issue rather than a clear code defect
  — flagged for the user to watch for on a re-run rather than guessed at blindly.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 289/289 passed (287 previous + 2 net new).
- Result: **Pass.** Worth keeping as an example of the value of reviewing multiple traces of the same
  failure together (all three independently showed the same Start-button replan pattern) rather than
  fixing only what the most recent error message pointed at.

### [2026-08-02] Debug pass — the hotkey fix worked; a new race appeared one step later
- Files checked: `src/action/mouse_keyboard.py`, `src/brain/orchestrator.py`'s `_execute_and_verify()`,
  plus the user's latest trace log.
- Confirmed first: the previous entry's `hotkey`-for-Start-menu fix worked correctly (via replay from a
  matching prior episode) -- no replan needed for step 1 at all, a clean improvement over every prior
  trace. This ruled out the hotkey change as the source of the new failure and pointed at what came next
  instead.
- Issue found: `type("notepad")` followed immediately by `hotkey(["enter"])` — the pixel-diff verification
  in `_execute_and_verify()` correctly detected no visible screen change after Enter (the search-results
  panel likely hadn't finished populating yet), triggering a replan. But the replanner's correction (a
  click on `target_text: "Notepad"`) then failed too, because by the time it executed, the Start menu state
  had shifted enough that OCR found nothing. This ping-ponged between "press Enter again" and "click
  Notepad" until the replan budget was exhausted. Traced the root cause to `mouse_keyboard.py`:
  `click_at()`/`double_click_at()` already settle for 0.3s after acting (a real fix from earlier in this
  session), but `type_text()` and `press_hotkey()` had no equivalent settle at all -- so a type-then-hotkey
  sequence had nothing slowing it down to let Windows' UI catch up.
- Fixed by adding the same settle-delay pattern to both methods (`_POST_TYPE_OR_HOTKEY_SETTLE_SECONDS =
  0.4`), rather than tuning the replanner's retry logic, since the actual defect is upstream of
  verification entirely — the action fired before the UI had a chance to respond, so no amount of replan
  cleverness downstream would reliably fix it.
- Issues NOT fixed / still open: the user has not yet re-run the desktop task to confirm the settle delay
  actually resolves this specific race in practice, rather than just plausibly explaining it.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 291/291 passed (289 previous + 2 new).
- Result: **Pass.** Fourth time today this exact family of bug (an instant OS-level action racing ahead of
  a real, variable-latency Windows UI transition) has been found and fixed in a different specific spot —
  worth noting as a pattern: any new action type added to `mouse_keyboard.py` in the future should default
  to a settle delay unless there's a specific reason not to, rather than waiting for each one to be found
  live individually.

### [2026-08-02] Debug pass — Phase 10's own mining query was broken before it could mine anything real
- Files checked: `src/observability/trace_replay.py`, `src/brain/orchestrator.py`'s risk-logging call
  sites, plus every real Phase 7 trace log reconstructed from this session's earlier live-run exchanges.
- Approach: rather than assume `unclassified_or_missing_risk()` (built in an earlier phase, never actually
  run against real data before now) worked correctly, ran it for real first. It immediately produced
  obviously-wrong output: 5 "gaps" in a single 7-step trace, including a step that had already succeeded
  on an earlier attempt.
- Issues found:
  1. `unclassified_or_missing_risk()` flagged terminal `"done"` steps (which never get risk-classified by
     design) and every intermediate replan-retry log line for a step_num that got retried (only the FINAL
     entry for a step_num is what risk classification actually applies to). Fixed with an
     exclude-done-actions filter and a last-entry-per-step_num deduplication pass.
  2. Investigating why so many "final" entries still lacked risk even after fix #1 led to
     `orchestrator.py`: risk WAS being classified before every step executed, but the three error-path
     `log_step()` calls in `run_task()` (and the two equivalents in the replay loop) never threaded the
     already-computed `risk` variable through — every error-terminated step logged `risk: null`
     regardless of what tier it had actually been classified into. Fixed by passing `risk=risk` to all
     five call sites.
  3. After both fixes, re-ran the mining query against the same real data: zero denied gate decisions,
     zero edited gate decisions, zero genuine unclassified-risk gaps. Confirmed this is the honest,
     correct result — not a tool failure — since every real task so far completed without the user ever
     needing to deny or edit a step.
- Issues NOT fixed / not attempted: no real correction data exists yet to inform any change to
  `semantic_matcher.py`'s exemplar banks, so none was added or fabricated. This remains open until a real
  denied/edited gate decision or a genuine unclassified-risk case occurs in actual usage.
- Tests run: `python -m pytest -q --ignore=tests/gui` — 333/333 passed (320 previous + 13 new).
- Result: **Pass**, with two more real bugs found and fixed (bringing this session's live-data-driven bug
  count well past ten) — and, distinctly from every prior entry today, an honest negative result reported
  as the actual outcome of the phase rather than forced into a positive one.
