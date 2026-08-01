# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 5 — Hardening, complete. Plus: native Windows GUI (PySide6) added 2026-07-12, ahead of GPU model
training per the user's stated plan (build the GUI now, train once real usage data exists). Plus
(2026-08-01): a zero-dependency semantic risk/boundary layer and an offline real-pixel integration harness
(`tests/integration/`) — the latter immediately found and fixed a genuine OCR bug (see below). Plus
(2026-08-01, Phase 6 of `docs/PHASES.md`): the semantic layer is now actually live-wired into the
orchestrator (`RISK_MODEL_BACKEND=semantic` in `config.py`, `_check_boundary()`'s always-on second layer)
— previously it only ran inside the eval harness. Non-GUI suite: 195 → 229 tests passing (+34: 18
semantic-layer, 6 real-pixel integration, 2 OCR regression, 8 Phase-6 wiring) — verified with
`python -m pytest -q --ignore=tests/gui` in a build environment without PySide6/a display; the 232-test
full-suite figure from 2026-07-13 (which includes the 38 GUI tests) was not re-verified in this same
environment and should be re-confirmed on a machine with PySide6 installed before being combined with the
above. Still not yet run live against a real screen/OS/mouse-keyboard/LLM/display on the user's actual
Windows machine (same blocker throughout this project, and the next scheduled item — `docs/PHASES.md`
Phase 7) — but as of 2026-08-01, real Tesseract OCR and real `screen_diff` have now been exercised against
real rendered pixels via headless Chromium, which is a meaningfully closer proxy than the fully-synthetic
data every earlier test used, even though it is not yet the full live system.**

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
| `src/config.py` | 1.1 (updated Phase 6, 2026-08-01) | Complete (`risk_model_backend` accepts `"semantic"`) |
| `src/doctor.py` | Phase 7 prep (2026-08-01) | Complete — pre-flight diagnostic (`python -m src.doctor`), checks Tesseract/Playwright/config/writable-dirs/semantic-layer without executing a real task. Not a substitute for Phase 7 itself. |
| `requirements.txt` | 1.1 | Complete |
| \`src/brain/orchestrator.py\` | 1.2 (updated 2.3, 3.1, Phase 4, Phase 6) | Complete (Phase 2 verify/replan + Phase 3 episodic replay + Phase 4 edit-learning + Phase 6 always-on semantic boundary layer wired in) |
| `src/brain/planner.py` | 1.2 (updated Phase 4) | Complete (HostedLLMPlanner + optional LocalPlanner) |
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 5 rule-table expansion + read-only guard) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete (review_and_learn wired to memory) |
| `src/action/playwright_driver.py` | 1.3 | Complete (fixed real profile-launch bug found via live GUI run, 2026-07-13) |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 | Complete |
| `src/confirmation/gate.py` | 1.4 | Complete |
| `src/confirmation/prompt_ui.py` | 1.4 | Complete |
| `src/observability/logger.py` | 1.5 (updated Phase 4) | Complete (LoopAudit + log_event, llm_call accuracy) |
| `src/observability/trace_replay.py` | 5 | Complete |
| \`src/perception/ocr.py\` | 2.1 (updated 2026-08-01) | Complete (fixed real bug: `textord_min_linesize` config added — Tesseract's layout analysis was discarding solid-color button blocks as non-text before OCR ran) |
| \`src/perception/element_detector.py\` | 2.1 | Complete |
| \`src/perception/screen_diff.py\` | 2.1 | Complete |
| `src/memory/episodic_store.py` | 3.1 (updated Phase 4) | Complete (edited flag + flagged_for_review) |
| `src/memory/semantic_store.py` | 3.2 | Complete |
| `src/memory/memory_api.py` | 3.2 (updated Phase 4) | Complete |
| `src/brain/research_router.py` | 4.1 | Complete |
| `src/brain/semantic_matcher.py` | Improvement pass (2026-08-01) | Complete (dependency-free char-n-gram cosine similarity, backs `SemanticRiskJudge`/`semantic_boundary_match`) |
| `src/gui/style.py` | GUI (2026-07-12) | Complete |
| `src/gui/app.py` | GUI (2026-07-12) | Complete |
| `src/gui/main_window.py` | GUI (2026-07-12) | Complete (full dashboard: composer + trace + stats + memory) |
| `src/gui/worker.py` | GUI (2026-07-12) | Complete (background QThread + cross-thread confirmation bridge) |
| `src/gui/gui_logger.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/task_composer.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/trace_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/stats_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/memory_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/confirmation_dialog.py` | GUI (2026-07-12) | Complete |
| `requirements-gui.txt` | GUI (2026-07-12) | Complete (separate from requirements.txt, PySide6 only) |
| `tests/` | ongoing | In progress (non-GUI: 240 passing — 195 Phases 1-5/GUI-facade/playwright + 18 semantic-layer + 6 real-pixel integration + 2 OCR regression + 8 Phase-6 wiring + 11 doctor tool; see note above re: 38 GUI-only tests not re-verified this session) |
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
| `eval/adversarial_boundary_eval.py` + `eval/adversarial_cases.jsonl` | Complete, tested, already caught 2 real bugs in `risk_classifier.py` on first run |
| `training/prepare_dataset.py` | Complete, tested, runs today (real data is empty/tiny until live usage exists) |
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
desktop-target-type task → capture the trace log → report back). Non-GUI suite: 229 → 240 tests passing.
**Phase 7 itself remains not done** — this only prepares for it; the actual live run requires the user's
Windows machine and cannot be completed or verified here.
