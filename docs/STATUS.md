# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 10 — Track B data bootstrap, COMPLETE (2026-08-02) with an honest zero result.** Phases 1–5
complete; native Windows GUI added 2026-07-12; Phase 6 (semantic layer live-wired) complete 2026-08-01;
Phase 7 (first real live validation) complete 2026-08-02 — both browser and desktop paths completed a task
end-to-end with zero errors after nine real bugs found and fixed; Phase 8 (encryption-at-rest via Windows
DPAPI + log retention) complete and **confirmed working on the user's real Windows machine**; Phase 9
(injection-aware, non-blocking risk signal) complete. Full reasoning for all in `docs/DECISIONS.md`'s
2026-08-01/2026-08-02 entries. **Phase 10 mined real Phase 7 trace data for risk-classification correction
signal and found two more real bugs before it found any actual data**: `trace_replay.py`'s
`unclassified_or_missing_risk()` was flagging terminal `"done"` steps and intermediate replan-retry log
lines as false gaps (fixed with an exclusion + last-entry-per-step deduplication), and every
error-terminated step was logging `risk: null` even though risk had already been classified, because five
call sites in `orchestrator.py` never threaded the already-computed value through (fixed). After both
fixes, the honest result across every real trace available: **zero denied gate decisions, zero edited gate
decisions, zero genuine unclassified-risk gaps** — nothing was added to `semantic_matcher.py`'s exemplar
banks, since there's genuinely nothing real to add yet. `training/mine_corrections.py` (new) is built,
tested, and ready to surface real candidates the first time a user actually denies/edits a step or a
genuine classification gap occurs. Non-GUI suite: 195 → 333 tests passing, verified with
`python -m pytest -q --ignore=tests/gui` in a build environment without PySide6/a display; the 232-test
full-suite figure from 2026-07-13 (which includes 38 GUI tests) was not re-verified in this same
environment. **Still open:** real Windows DPI/multi-monitor scaling unverified; `src/gui/worker.py`'s
Phase-7-fix port unverified; Phase 9's injection signal is a phrase-bank heuristic with the same limits as
the original risk-classifier keyword floor; Phase 10's own success criterion (a measurable eval-recall
improvement from real-data-informed exemplars) is explicitly NOT met, since no real correction data exists
yet — `training/prepare_dataset.py`/`train_lora.py` remain blocked on a GPU regardless. Next up: Phase 11
(packaging & distribution).**

## Documentation files (`docs/` + root)

| File | Status | Notes |
|---|---|---|
| `context.md` | Complete | Root instruction file |
| `docs/README.md` | Complete | |
| `docs/PHASES.md` | Complete | Defines full file tree ahead of implementation |
| `docs/DECISIONS.md` | Complete (ongoing) | Append-only, updated every future file change |
| `docs/STATUS.md` | Complete (ongoing) | This file |
| `docs/DESIGN.md` | Complete | Visual design system for confirmation UI/dashboard |
| `docs/TRD.md` | Complete | |
| `docs/APPFLOW.md` | Complete | |
| `docs/WORKFLOW.md` | Complete | |
| `docs/DEBUG.md` | Complete | |
| `docs/CODE_LOGIC.md` | Complete | Covers all 19 reviewed repos incl. 2 exclusions; adds `research_router.py` and `LoopAudit` to Phase 4 in `PHASES.md` |
| `docs/PHASE_7_CHECKLIST.md` | Complete (2026-08-01) | Step-by-step guide for the user's own Phase 7 live run — not executable/verifiable from this build environment |

## Source files (`src/`) — not yet created

| File | Phase | Status |
|---|---|---|
| `src/main.py` | 1.1 (updated Phase 6, 2026-08-01) | Complete (`_build_risk_model_judge` adds `"semantic"` branch — no endpoint needed) |
| `src/config.py` | 1.1 (updated Phase 6, 2026-08-01, Phase 8, 2026-08-02) | Complete (`risk_model_backend` accepts `"semantic"`; `log_retention_days` added) |
| `src/doctor.py` | Phase 7 prep (2026-08-01), updated Phase 8 (2026-08-02) | Complete — pre-flight diagnostic (`python -m src.doctor`), checks Tesseract/Playwright/config/writable-dirs/semantic-layer/encryption-at-rest without executing a real task. Not a substitute for Phase 7 itself. |
| `requirements.txt` | 1.1 | Complete |
| \`src/brain/orchestrator.py\` | 1.2 (updated 2.3, 3.1, Phase 4, Phase 6, Phase 9) | Complete (Phase 2 verify/replan + Phase 3 episodic replay + Phase 4 edit-learning + Phase 6 always-on semantic boundary layer + Phase 9 non-blocking injection-signal check, both wired in) |
| \`src/brain/boundary_guard.py\` | 1.0 (updated Phase 6, Phase 9) | Complete (hard-boundary `check()` + Phase 9's non-blocking `check_injection_signal()`, deliberately kept separate) |
| `src/brain/planner.py` | 1.2 (updated Phase 4) | Complete (HostedLLMPlanner + optional LocalPlanner) |
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 5 rule-table expansion + read-only guard) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete (review_and_learn wired to memory) |
| `src/action/playwright_driver.py` | 1.3 (updated 2026-08-01) | Complete (fixed real profile-launch bug found via live GUI run, 2026-07-13; made Chrome launch lazy — `is_launched` property — after a desktop-only live task was needlessly blocked by a Chrome launch failure) |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 (updated 2026-08-01, 2026-08-02) | Complete (real focus-verification + periodic active-reactivation before typing + post-action settle delay on type/hotkey, all found/fixed via Phase 7 live runs) |
| `src/confirmation/gate.py` | 1.4 (updated 2026-08-01) | Complete (fixed CLI unrecognized-input-silently-approves bug; added opt-in `auto_approve_external`, never applies to Destructive) |
| `src/confirmation/prompt_ui.py` | 1.4 | Complete |
| `src/observability/logger.py` | 1.5 (updated Phase 4, updated Phase 8, 2026-08-02) | Complete (LoopAudit + log_event, llm_call accuracy; `prune_old_logs()` day-based retention for trace logs/screenshots) |
| `src/observability/trace_replay.py` | 5 (updated Phase 10, 2026-08-02) | Complete (`unclassified_or_missing_risk()` fixed — real bug found mining actual trace data, was flagging `done` steps and replan-retry noise as false gaps) |
| \`src/perception/ocr.py\` | 2.1 (updated 2026-08-01) | Complete (fixed real bug: `textord_min_linesize` config added — Tesseract's layout analysis was discarding solid-color button blocks as non-text before OCR ran) |
| \`src/perception/element_detector.py\` | 2.1 | Complete |
| \`src/perception/screen_diff.py\` | 2.1 | Complete |
| `src/memory/episodic_store.py` | 3.1 (updated Phase 4, updated 2026-08-01, updated Phase 8 2026-08-02) | Complete (edited flag + flagged_for_review + `STEP_SCHEMA_VERSION` replay gate + Windows-DPAPI encryption-at-rest via `src/security/at_rest.py`) |
| `src/memory/semantic_store.py` | 3.2 (updated Phase 8, 2026-08-02) | Complete (Windows-DPAPI encryption-at-rest via `src/security/at_rest.py`) |
| `src/security/at_rest.py` | Phase 8 (2026-08-02) | Complete — Windows DPAPI wrapper (`protect`/`unprotect`/`is_available`), degrades to plaintext with a one-time warning on non-Windows. Only tested against a reversible fake `win32crypt`, not real DPAPI. |
| `src/memory/memory_api.py` | 3.2 (updated Phase 4) | Complete |
| `src/brain/research_router.py` | 4.1 | Complete |
| `src/brain/semantic_matcher.py` | Improvement pass (2026-08-01) | Complete (dependency-free char-n-gram cosine similarity, backs `SemanticRiskJudge`/`semantic_boundary_match`) |
| `src/gui/style.py` | GUI (2026-07-12) | Complete |
| `src/gui/app.py` | GUI (2026-07-12) | Complete |
| `src/gui/main_window.py` | GUI (2026-07-12) | Complete (full dashboard: composer + trace + stats + memory) |
| `src/gui/worker.py` | GUI (2026-07-12, updated 2026-08-01) | Complete (background QThread + cross-thread confirmation bridge; ported `TESSERACT_CMD`/`auto_approve_external` wiring from `main.py`, found missing during a lazy-launch spot-check — unverified in this build environment, PySide6 unavailable) |
| `src/gui/gui_logger.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/task_composer.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/trace_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/stats_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/memory_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/confirmation_dialog.py` | GUI (2026-07-12) | Complete |
| `requirements-gui.txt` | GUI (2026-07-12) | Complete (separate from requirements.txt, PySide6 only) |
| `tests/` | ongoing | In progress (non-GUI: 333 passing — 195 Phases 1-5/GUI-facade/playwright + 18 Phase-6 semantic-layer/wiring + 6 real-pixel integration + 2 OCR regression + 70 Phase-7 live-bug-fix tests + 19 Phase-8 encryption-at-rest/retention tests + 10 Phase-9 injection-signal tests + 13 Phase-10 mining-tool tests (see `docs/DECISIONS.md`'s 2026-08-01/02 entries for the 11 total bugs these cover); see note above re: 38 GUI-only tests not re-verified this session) |
| `tests/integration/` | Improvement pass (2026-08-01) | New — offline real-pixel harness: real headless Chromium + real Tesseract + real `screen_diff`, no mocks. Requires Playwright's Chromium install + Tesseract binary; `pytest --ignore=tests/integration` to skip, same convention as `tests/gui/` |

## Known blockers
- Live end-to-end run (real screen capture, real Tesseract OCR, real mouse/keyboard control, real Gemini
  API call) not yet performed in this environment — 97 unit tests pass and all modules import cleanly, but
  a Windows display, the Tesseract binary, and a real `GEMINI_API_KEY` are required for a true live run,
  which is on the user's machine, not this build environment. Episodic replay's matching quality (the 0.82
  difflib threshold in `episodic_store.py`) and the new `corrections:<action>` semantic-memory namespace
  have only been validated against unit-test phrasing/edits — real usage logs from Phase 5 hardening may
  warrant retuning both. `LocalPlanner`/`build_http_generate_fn` are wired in but untested against a real
  local model server (no such server available in this build environment). **(2026-08-01 update:** real
  Tesseract OCR and real `screen_diff` are no longer purely-mocked-only — see `tests/integration/` and the
  Known gaps section below — but real mouse/keyboard control, real DPI/multi-monitor scaling, and a real
  Gemini API call remain unverified in any environment to date.)

## Known gaps (honest remainder after the 2026-07-12 remediation pass)
This project underwent an independent line-by-line gap review, and every concretely fixable issue found
was fixed and tested (see `docs/DECISIONS.md` and `docs/DEBUG.md` entries dated 2026-07-12). What's
listed below is what remains, stated plainly rather than glossed over:

- **Zero live validation against the real OS/display — still true; perception-layer validation against
  real pixels is now partially closed (2026-08-01).** `tests/integration/` now runs real Tesseract OCR and
  real `screen_diff.compare()` against real headless-Chromium screenshots, and it immediately found and
  fixed a genuine bug (Tesseract's `textord` layout analysis was discarding solid-color button blocks as
  non-text before OCR ran — see `docs/DECISIONS.md`/`docs/DEBUG.md` 2026-08-01 entries). What this does
  NOT cover, still fully unknown: real OS-level mouse/keyboard control and click-coordinate precision,
  real Windows DPI/multi-monitor scaling behavior, and a real Gemini API call — all still require the
  user's actual Windows machine.
- **The hard-boundary guard (`boundary_guard.py`) is still keyword/phrase-based as its primary mechanism,
  now with an additive (not replacing), live-wired semantic layer (2026-08-01, Phase 6).**
  `semantic_boundary_match()` in `risk_model_backend.py` now actually runs inside
  `orchestrator._check_boundary()` on every task, not just in the eval harness — catches paraphrased
  boundary-evasion attempts the keyword table misses (`boundary_evasion` eval recall 14% → 71%), but it's
  still exemplar-similarity matching, not a trained classifier — sufficiently novel phrasing, or an attack
  crafted specifically against its known exemplar list, could still slip through both layers. Closing this
  completely would still require a fundamentally different mechanism (a dedicated trained classifier, i.e.
  Track B), which remains out of scope for this pass.
- **Screenshots and logs are still unencrypted at rest.** Credential-shaped `params` values are now
  redacted before being written (fixed this pass), but full-frame screenshots can still contain
  arbitrary on-screen sensitive content (open messages, visible form fields, etc.), and there is no
  retention policy or encryption-at-rest for the `logs/` directory. This is a larger, deliberate
  design/infra decision (key management, where to store keys, etc.) that wasn't attempted here.
- **No multi-user / concurrency model.** Single process, single browser profile, one task at a time,
  by design — not addressed in this pass.
- **The "no de-safetied base model" boundary is enforced by review process, not runtime code** — see
  `boundary_guard.py`'s own docstring, which says this honestly rather than pretending to check
  something a keyword scan over step text structurally cannot see (which model is configured is a
  property of `config.py`, not of any individual step).
- **The LLM risk-judge fallback (`risk_llm_judge.py`) adds a real second opinion, but it costs an extra
  LLM call for every step the keyword filter finds no signal on**, and its own judgment is still an LLM
  call subject to the same general LLM failure modes (it fails safe to "no opinion" on any error, but a
  confidently wrong "local" verdict from the judge is not distinguishable from a correct one without
  human review of the trace).

## Track B: trained-model architecture (new, 2026-07-12)
Two SEPARATE trained-model interfaces now exist, both currently disabled by default (no runtime
behavior change until a human explicitly opts in via `.env`):

| File | Status |
|---|---|
| `src/brain/planner.py`'s `LocalFineTunedPlanner` | Interface + wiring complete; no model trained yet |
| `src/brain/risk_model_backend.py`'s `LocalFineTunedRiskModel` | Interface + wiring complete; no model trained yet |
| `eval/adversarial_boundary_eval.py` + `eval/adversarial_cases.jsonl` | Complete, tested, already caught 2 real bugs in `risk_classifier.py` on first run. Phase 9 (2026-08-02) added a 5th case category (`prompt_injection`, 6 cases) scored separately by the new `eval/injection_signal_eval.py` (100% accuracy on its own case set), not folded into this harness since it scores a different kind of output (binary signal vs. risk/boundary verdict). |
| `training/prepare_dataset.py` | Complete, tested, runs today (real data is empty/tiny until live usage exists) |
| `training/mine_corrections.py` | Complete (Phase 10, 2026-08-02) — mines real trace logs for denied/edited gate decisions and genuine unclassified-risk gaps; run for real against reconstructed Phase 7 data, found two real bugs in the underlying query/logging before finding any actual correction data, then reported an honest zero-candidate result. Never auto-modifies `semantic_matcher.py`. |
| `training/train_lora.py` | Complete, correct, NOT runnable in this sandbox (no GPU) — ready for a real training machine |
| `training/model_card_template.md` | Template ready; no model card filled out yet (no model trained yet) |

**Current keyword-only baseline eval score** (`python -m eval.adversarial_boundary_eval`): ~40% overall
accuracy, with `evasive_destructive` and `boundary_evasion` recall in the 14% range specifically. This is
the expected, honest starting point — see `eval/README.md`'s "Known baseline gaps" section — and is the
actual justification for training `LocalFineTunedRiskModel`, not a problem to solve by adding more
keywords to `risk_classifier.py`.

**Update (2026-08-01):** a zero-dependency semantic layer (`SemanticRiskJudge`/`semantic_boundary_match`
in `risk_model_backend.py`, scored via `python -m eval.adversarial_boundary_eval --model semantic`) now
scores 73% overall, 71% on `evasive_destructive`/`boundary_evasion` each, with no change to
`benign_but_tricky`'s false-positive rate. This is a real, same-day, zero-cost improvement to the baseline
everything else in this table is measured against — **it does not satisfy the deployment gate below or
replace the need to train `LocalFineTunedRiskModel`.** 71% recall on the two highest-stakes categories is
nowhere near the ≥0.95 thresholds in `eval/README.md`; see that file's 2026-08-01 update for the full
breakdown and the explicit statement of what this addition does and doesn't change.

**Nothing may be set to `RISK_MODEL_BACKEND=local` in a live `.env` until:**
1. A real model has actually been trained (`training/train_lora.py` run on real hardware with real data).
2. `eval/adversarial_boundary_eval.py --model local` clears the thresholds in `eval/README.md`.
3. `training/model_card_template.md` is filled out and committed.
4. A `docs/DECISIONS.md` entry records the decision, per `docs/TRD.md §6.1`.

## Next action
1. **Still outstanding from Phase 5 (unchanged by this pass):** run the system live end to end to
   generate real `logs/task_*.jsonl` traces — this remains the single biggest unblocking step for
   almost everything else in this project, including Track B's training data.
2. **Track B specifically:** once real logs exist, mine corrections out of them via
   `trace_replay.py`'s `unclassified_or_missing_risk()`, feed them into
   `training/prepare_dataset.py --target risk_model`, and run `training/train_lora.py` on a real GPU
   machine. Do the same for the planner once enough successful (`status="done"`) episodes exist in
   `memory/episodic_store.py`'s database. Run the eval gate before enabling either trained backend in a
   live `.env`, and fill out a model card per `training/model_card_template.md` for each.

---
**Last updated:** 2026-07-12 (Track B added: `risk_model_backend.py` (new, a genuinely separate
`RiskModelBackend` interface from `PlannerBackend`, additive-only over the keyword floor); `LocalPlanner`
renamed to `LocalFineTunedPlanner` (backward-compat alias kept); `config.py` gained independent
`risk_model_backend`/`local_risk_model_endpoint` fields so the two models can be swapped/rolled back
separately; built and ran `eval/adversarial_boundary_eval.py` + `eval/adversarial_cases.jsonl`, which
immediately caught two real bugs in `risk_classifier.py`'s read-only-guard logic (both fixed); added
`training/` scaffold (`prepare_dataset.py`, `train_lora.py`, `model_card_template.md`,
`requirements-training.txt`) for the two separate LoRA fine-tuning runs; added `docs/TRD.md §6.1` making
trained-model provenance auditable via the model card + eval gate. 189 tests passing total, 24 new. See
"Track B" section above for exactly what is and isn't done, and "Known gaps" further above for what
remains from the prior pass.)

---
**Update 2026-07-12 (this session):** Re-verified this project end-to-end after being adopted as the
working codebase: clean venv + exact pinned `requirements.txt` install succeeded, all 189 tests pass, all
29 `src/` modules import cleanly, `eval/adversarial_boundary_eval.py` baseline reproduces the documented
~40% overall / 14% evasive-category accuracy. Design system replaced: `docs/DESIGN.md` now points to the
"Steep" token system (`docs/design-tokens/`) instead of the old console color scheme — no `src/` GUI code
exists yet, this only affects future GUI implementation. Still true: zero live task runs have ever
happened (see "Next action" above) — this remains the single biggest unblocking step, unchanged by this
verification pass.

---
**Update 2026-07-12 (GUI added, same session):** Built the native Windows GUI (`src/gui/`, PySide6) per the
user's choice — full dashboard scope. 41 `src/` modules now import cleanly (up from 29); 227 tests passing
(189 + 38 new). Two real bugs found and fixed during this pass: (1) `MemoryPanel` initially reached into
`MemoryAPI`'s private `_semantic` attribute — fixed by adding a proper public `all_preferences()` method to
both `SemanticStore` and `MemoryAPI`; (2) `ConfirmationDialog` initially used `QWidget.isVisible()` to
detect edit-mode, which is unreliable outside a fully shown window — fixed with an explicit boolean flag.
The cross-thread confirmation bridge (`GateBridge`, using `Qt.BlockingQueuedConnection`) was specifically
stress-tested with a real `QThread` to rule out a deadlock. GPU model training is intentionally still
untouched, per the user's own stated plan (GUI first, training once real usage data exists) — see
`training/README.md` for that plan's own prerequisites, which this GUI work does not change or shortcut.

---
**Update 2026-07-13 (first live run):** The user ran a real task through the GUI for the first time —
this is the milestone `docs/STATUS.md` had flagged as the single biggest blocker throughout the whole
project. It surfaced one real bug that no amount of unit testing had caught: `PlaywrightDriver` was
launching against a freshly-created empty Chrome profile instead of the user's real, already-logged-in
one (root cause: `user_data_dir` was built as `profiles_dir/profile_name` instead of using
`--profile-directory` against the real "User Data" root). Fixed, with a new regression test
(`tests/action/test_playwright_driver.py`) that mocks `sync_playwright` directly and asserts the exact
launch arguments — the first test in this project to actually verify what gets passed to Chromium, rather
than mocking one layer above it. Also removed the "Est. cost" card from the GUI's Loop Audit panel per
user request (still tracked internally, just not displayed). 232 tests passing total.

---
**Update 2026-08-01 (semantic layer + real-pixel harness):** Added a zero-dependency, char-n-gram-based
semantic risk/boundary layer (`src/brain/semantic_matcher.py`, `SemanticRiskJudge`/`semantic_boundary_match`
in `risk_model_backend.py`) that raises the adversarial eval from 40% to 73% overall without any training
data or GPU — explicitly not a substitute for Track B's trained model or its deployment gate, see
`eval/README.md`. Also added `tests/integration/`, this project's first tier to exercise real Tesseract OCR
and real `screen_diff` against real headless-Chromium screenshots instead of synthetic data — it found and
fixed a genuine bug on its first run (Tesseract's layout analysis discarding solid-color button blocks as
non-text before OCR ran; fixed with `-c textord_min_linesize=1.0` in `ocr.py`). Non-GUI suite: 195 → 221
tests passing (verified with `pytest --ignore=tests/gui` in a build environment without PySide6; the 232
GUI-inclusive figure above was not re-verified this session). Full details in `docs/DECISIONS.md` and
`docs/DEBUG.md`'s 2026-08-01 entries. Still outstanding, unchanged by this pass: real OS mouse/keyboard
control, real DPI/multi-monitor scaling, and a real live end-to-end run on the user's actual Windows
machine.

---
**Update 2026-08-01 (Phase 6 — semantic layer live-wired):** The semantic layer above previously only ran
inside `eval/adversarial_boundary_eval.py`; it now actually runs on live task execution. `config.py`'s
`risk_model_backend` accepts `"semantic"` (no endpoint needed), `main.py` wires it to `SemanticRiskJudge`
the same way `"hosted"`/`"local"` are wired, and `orchestrator._check_boundary()` now always runs
`semantic_boundary_match()` as a second layer after the keyword `boundary_guard.check()` — additive only,
logged with `detected_by: "keyword" | "semantic"` so either layer's catch is auditable. Non-GUI suite:
221 → 229 tests passing (+8, covering the new config value, the new builder branch, and two orchestrator-
level proofs that the boundary layer both catches what keyword misses and doesn't double-fire when keyword
already caught something). Full details in `docs/DECISIONS.md`'s 2026-08-01 Phase 6 entry;
`docs/PHASES.md`'s Phase 6 marked complete. Phase 7 (first real live validation on Windows) is next and
unchanged by this pass — none of this wiring has been exercised against a real Gemini call or real
confirmation dialog yet, only mocks.

---
**Update 2026-08-01 (Phase 7 prep — not the live run itself):** Added `python -m src.doctor`, a pre-flight
diagnostic checking every Phase 7 environment prerequisite (Tesseract on PATH, Playwright Chromium
launches, config/API key loads, writable dirs, Phase 6's semantic layer) without executing a real task —
and `docs/PHASE_7_CHECKLIST.md`, the ordered step-by-step sequence for the user's own live run (doctor tool
→ verify the real Chrome profile per the 2026-07-13 profile-bug lesson → browser-only task first →
desktop-target-type task → capture the trace log → report back). Non-GUI suite: 229 → 244 tests passing.
**Phase 7 itself remains not done** — this only prepares for it; the actual live run requires the user's
Windows machine and cannot be completed or verified here.

---
**Update 2026-08-01 (Phase 7 — first real live runs, two real bugs found and fixed):** The user completed
the first real task runs in this project's history. Browser task: hit a transient truncated-JSON crash on
attempt one, succeeded on attempt two by hand — fixed with a bounded one-retry in both
`HostedLLMPlanner.next_step()` and `LocalFineTunedPlanner.next_step()`. Desktop task: failed on the first
click because the planner used the web-schema `selector` key instead of `target_text` for a desktop step
— `SYSTEM_PROMPT` never actually distinguished the two schemas; fixed the prompt and added a defensive
`selector`→`target_text` fallback in `action_router.py`. Non-GUI suite: 244 → 249 tests passing. Full
details in `docs/DECISIONS.md`/`docs/DEBUG.md`'s matching 2026-08-01 entries. **Phase 7 is in progress, not
complete** — the confirmation gate and browser path are now confirmed working end-to-end on real hardware,
but the desktop task has not yet been re-run against these fixes to confirm a full desktop task completes
cleanly; DPI/multi-monitor scaling also remains unverified.

---
**Update 2026-08-01 (first fully-completed desktop task — two more bugs, one safety-relevant):** The user
re-ran the desktop task and it completed with `status: done` — the first fully-completed desktop task in
this project's history. But the trace/transcript revealed two more real bugs. **Safety-relevant:**
`prompt_ui.console_prompt()` silently treated ANY unrecognized input (a typo, a blank Enter) as approval —
confirmed live when a typo (`Notepad`) at the gate prompt was recorded as `"verdict": "approved"`. Fixed by
looping until a real approve/deny/edit answer is given; confirmed the GUI dialog never had this problem
(it already defaults to denied). **Correctness-relevant:** the typed test message was found printed in the
terminal after the process exited, not inside Notepad — `mouse_keyboard.py`'s `type_text()` had no
verification that the intended window actually had focus before typing. Fixed with a real active-window
poll (`expect_window_contains`, wired through `action_router.py` and `SYSTEM_PROMPT`) that raises rather
than typing into the wrong window if the expected one never gains focus. Non-GUI suite: 249 → 258 tests
passing. Full details in `docs/DECISIONS.md`/`docs/DEBUG.md`'s matching entries. Phase 7 success criterion
is now substantially met for both paths; not yet done: re-confirming the message lands in Notepad with
these newest fixes, and DPI/multi-monitor scaling remains unverified.

---
**Update 2026-08-01 (episodic replay was silently undoing the fix + window re-activation +
AUTO_APPROVE_EXTERNAL):** The user re-ran the desktop task and the message landed in the terminal again —
the trace showed why: `"llm_call": false` and `"source_episode_id": 6, "match_score": 1.0"`. Replay had
matched a PRE-FIX episode and reused its stored steps verbatim, bypassing the planner (and the previous
entry's `expect_window_contains` fix) entirely. Root-caused and fixed with a `STEP_SCHEMA_VERSION` gate on
`EpisodicStore.find_match()` — old episodes are permanently excluded from replay once the schema version is
bumped, forcing a fresh plan through the current (fixed) planner instead. Also added, per the user's own
diagnosis and explicit request: active window re-activation in `mouse_keyboard.py` (not just detection —
`type_text()` now tries once to reclaim focus for the expected window before giving up), and
`AUTO_APPROVE_EXTERNAL` (skips the External-risk prompt entirely when enabled; never applies to Destructive,
which keeps its confirm-phrase requirement unconditionally). Non-GUI suite: 258 → 270 tests passing. Full
details in `docs/DECISIONS.md`/`docs/DEBUG.md`'s matching entries. Not yet done: re-running the desktop task
against this combined set of fixes to confirm a clean end-to-end result.

---
**Update 2026-08-01 (Chrome launch made lazy — a desktop-only task was needlessly blocked by it; two
GUI-path gaps found):** The user's next attempt at the desktop task failed before any step ran, with a
`ChromeProfileLaunchError` — for a task that never uses a browser at all. Root cause: `main.py` launches
Chrome unconditionally for every task, and `orchestrator._observe()` called `driver.current_url()`/
`current_title()` on every step regardless of task type. Fixed together: `PlaywrightDriver` now only
launches Chrome on first real browser use (`is_launched` property added), and `_observe()` checks that
before calling into the driver, returning a placeholder instead of forcing a launch. A purely desktop-only
task now never touches Playwright/Chrome at all. While verifying the GUI's separate entry point didn't have
the same problem, found two unrelated real gaps: `src/gui/worker.py` never received either the
`TESSERACT_CMD` fix or the `AUTO_APPROVE_EXTERNAL` feature added earlier this session (it builds its own
`OCREngine`/`ConfirmationGate` independently of `main.py`) — both ported over. Non-GUI suite: 270 → 277
tests passing. Full details in `docs/DECISIONS.md`/`docs/DEBUG.md`'s matching entries. Not yet done:
re-running the desktop task to confirm it no longer depends on Chrome; the `worker.py` port is unverified in
any environment (GUI tests require PySide6).

---
**Update 2026-08-01 (Gemini 429 rate-limit crash fixed):** The user's next run hit a fresh unhandled crash —
`google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED` (their free-tier key allows only 5 requests/
minute). This exception type is unrelated to the parse-failure `ValueError` the existing retry catches, so
it was never handled. Added `_generate_with_rate_limit_retry()`: catches API errors specifically where
`code == 429`, reads the server's own suggested `retryDelay` from the error body, backs off and retries up
to 3 attempts, and raises immediately (no retry) for any other API error. Non-GUI suite: 277 → 281 tests
passing. Full details in `docs/DECISIONS.md`/`docs/DEBUG.md`'s matching entries. Does not raise the
underlying quota ceiling itself — a user hitting this often should slow down between tasks or move off the
free tier; the fix only prevents a single transient hit from crashing an otherwise-recoverable task.

---
**Update 2026-08-01 (rate-limit retry made configurable — previous default compounded into 10+ minutes):**
The user reported a task taking 10+ minutes to reach its first prompt — a direct consequence of the
previous update's fixed 3-attempt/uncapped backoff compounding across several rate-limited steps on a
heavily-throttled free-tier key. Rather than revert (which would reintroduce the earlier crash), made both
the attempt count and backoff cap configurable via `RATE_LIMIT_MAX_ATTEMPTS`/
`RATE_LIMIT_MAX_BACKOFF_SECONDS`, with a faster-failing default (2 attempts, capped at 20s, down from 3
uncapped) wired through both `main.py` and `src/gui/worker.py`. Setting `RATE_LIMIT_MAX_ATTEMPTS=1`
disables the retry entirely for a fail-fast experience. Non-GUI suite: 281 → 287 tests passing. Full
details in `docs/DECISIONS.md`'s matching entry. Not yet done: the user has not yet re-run the desktop task
to confirm the new defaults meaningfully shorten the wait in practice.

---
**Update 2026-08-02 (three trace logs reviewed together — Start-menu clicking made reliable via hotkey;
window re-activation made periodic):** The user shared three separate desktop-task traces. Confirmed first
that the 2026-08-01 `expect_window_contains` fix was working correctly (trace 3 properly caught VS Code
having focus instead of Notepad and refused to type) rather than assuming the error meant it was broken.
Found two real issues instead: (1) every trace needed a mid-task replan just to click the Start button —
`action_router.py` already had a working `hotkey` action, but `SYSTEM_PROMPT` never told the planner it
existed, so it always tried an unreliable OCR click on the small taskbar icon first. Fixed by documenting
`hotkey` and recommending `{"keys": ["win"]}` specifically for the Start menu. (2) The window-activation
fix only tried once, too early for a cold-launching app like Notepad to have created its window yet — fixed
with periodic retries across a longer (10s, up from 5s) timeout window. Non-GUI suite: 287 → 289 tests
passing. Full details in `docs/DECISIONS.md`'s matching entry. Not yet done: re-running the desktop task to
confirm the Start-menu step no longer needs a replan and Notepad reliably gains focus.

---
**Update 2026-08-02 (hotkey fix confirmed working; a new type-then-hotkey race found and fixed):** The
user's re-run confirmed the hotkey fix worked perfectly for opening the Start menu — no replan needed. A
new race then appeared one step later: `type("notepad")` immediately followed by `hotkey(["enter"])` fired
before Windows' search-results panel finished populating, so Enter did nothing; the resulting replan
correction (a click) then also failed since the Start menu state had shifted by then, and the task
eventually exhausted its replan budget. Root cause: `click_at()` already settles 0.3s after acting, but
`type_text()`/`press_hotkey()` had no equivalent delay. Fixed by adding the same settle pattern
(`_POST_TYPE_OR_HOTKEY_SETTLE_SECONDS = 0.4`) to both. Non-GUI suite: 289 → 291 tests passing. Full details
in `docs/DECISIONS.md`'s matching entry. Fourth instance today of this same bug family (instant action
racing a variable-latency Windows UI transition) — worth treating a settle delay as the default for any
future `mouse_keyboard.py` action rather than waiting to find each one live individually. Not yet done:
re-running the desktop task to confirm this specific race no longer occurs in practice.

---
**Update 2026-08-02 (Phase 7 COMPLETE):** The user re-ran the desktop task immediately after the settle-
delay fix above. Result: `status: done`, all 4 steps `executed`, **zero replans, zero errors** — the first
fully clean desktop-path run in this project's history. Replayed from a stable stored episode at $0.00
cost, itself a good sign the fixed step sequence is now trustworthy for reuse. This satisfies
`docs/PHASES.md`'s Phase 7 success criterion in full: one full task completing end-to-end on real Windows
hardware via each execution path (browser confirmed earlier, desktop confirmed now), with a real trace log
to inspect. **`docs/PHASES.md`'s Phase 7 is now marked COMPLETE.** Nine distinct real bugs were found and
fixed across this phase's live-run cycle — see `docs/DECISIONS.md`'s 2026-08-01/2026-08-02 entries for the
full list. Remaining open, unchanged by Phase 7: real Windows DPI/multi-monitor scaling has not been
exercised by any run so far, and the `src/gui/worker.py` port of Phase 7's CLI-path fixes remains
unverified in any environment. Next scheduled: Phase 8 (data security & retention).

---
**Update 2026-08-02 (Phase 8 COMPLETE — encryption-at-rest + log/screenshot retention):** Design decision
recorded first, per this phase's own requirement: Windows DPAPI over a user-managed passphrase or separate
key file (ties encryption to the current Windows user account, zero key management; full reasoning and
rejected alternatives in `docs/DECISIONS.md`). Implemented: `src/security/at_rest.py` (DPAPI wrapper,
degrades to plaintext with a one-time warning on non-Windows), `episodic_store.py`/`semantic_store.py`
(sensitive columns encrypted transparently, matching logic unaffected), `logger.py`'s new
`prune_old_logs()` (day-based retention, default 14 days, wired into both `main.py` and
`src/gui/worker.py` together this time), a new `config.py` field (`LOG_RETENTION_DAYS`), and a new
`src/doctor.py` encryption-availability check. Non-GUI suite: 291 → 310 tests passing, including tests
proving the raw SQLite bytes on disk don't contain plaintext when DPAPI is available, not just that the
wrapper round-trips in isolation. **`docs/PHASES.md`'s Phase 8 is now marked COMPLETE.** Not yet verified:
none of this has been exercised against real DPAPI — `pywin32` cannot be installed in this Linux build
environment, so every test uses a reversible fake standing in for `win32crypt`. The user should confirm on
their own Windows machine (after `pip install pywin32`) that `python -m src.doctor` reports encryption as
available, and that existing episodic/semantic memory continues to work correctly afterward. Next
scheduled: Phase 9 (injection-aware risk signal).

---
**Update 2026-08-02 (Phase 8 confirmed on real hardware):** The user ran `python -m src.doctor` on their
real Windows machine after `pip install pywin32`, and it reported encryption-at-rest as genuinely
available. Closes the "not yet verified against real DPAPI" caveat above.

---
**Update 2026-08-02 (Phase 9 COMPLETE — injection-aware risk signal):** New
`boundary_guard.check_injection_signal()` — a distinct, non-blocking signal for the different threat model
of attacker-controlled on-screen content, scored against a phrase bank of common prompt-injection framings.
Deliberately never gates execution by itself (unlike the hard-boundary `check()` beside it) — Phase 9's own
success criterion is that it's flagged distinctly in the trace log, not that it blocks anything. Wired into
`orchestrator.py`'s `_check_injection_signal()`, called on every step in both the normal and replay loops.
Added a 5th eval category (`prompt_injection`, 6 cases, independently written since no real captured attacks
exist yet) and a small dedicated scorer (`eval/injection_signal_eval.py`, 100% accuracy). Non-GUI suite:
310 → 320 tests passing. Full details in `docs/DECISIONS.md`'s matching entry. `docs/PHASES.md`'s Phase 9
marked complete. Still open: this is a phrase-bank heuristic (same limits as `risk_classifier.py`'s
original keyword floor) that only inspects a step's own description/params, not the raw page content the
planner actually read — a fully complete fix would need page-text extraction and diffing, out of scope
here. Next scheduled: Phase 10 (Track B data bootstrap).

---
**Update 2026-08-02 (Phase 10 COMPLETE — honest zero result):** Mined real Phase 7 trace data for risk-
classification correction signal and found two more real bugs first: `trace_replay.py`'s
`unclassified_or_missing_risk()` was flagging terminal `"done"` steps and intermediate replan-retry log
lines as false gaps (fixed with exclusion + last-entry deduplication), and `orchestrator.py` was logging
`risk: null` on every error-terminated step even though risk had already been classified, because five
call sites never threaded the computed value through (fixed). After both fixes, the honest result across
every real trace: zero denied gate decisions, zero edited gate decisions, zero genuine unclassified-risk
gaps. `semantic_matcher.py` was NOT modified — there's nothing real to add yet. New
`training/mine_corrections.py` is built, tested, and ready to surface real candidates automatically once
they exist. Non-GUI suite: 320 → 333 tests passing. Full details in `docs/DECISIONS.md`'s matching entry.
`docs/PHASES.md`'s Phase 10 marked complete, with its own success criterion explicitly NOT met (no real
data existed to inform any measurable eval improvement) rather than forced. Next scheduled: Phase 11
(packaging & distribution).
