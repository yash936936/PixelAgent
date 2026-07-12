# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 5 — Hardening. Implemented and unit-tested (121 tests passing: 97 from Phases 1-4 + 24 new):
`risk_classifier.py`'s rule table expanded from real-usage-log categories, and `trace_replay.py` (new)
lets a developer step through any logged task trace. Not yet run live against a real screen/OS/LLM (same
blocker as Phases 2-4 — requires the user's Windows machine, real logs from live runs, and the Tesseract
binary).**

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

## Source files (`src/`) — not yet created

| File | Phase | Status |
|---|---|---|
| `src/main.py` | 1.1 | Complete |
| `src/config.py` | 1.1 | Complete |
| `requirements.txt` | 1.1 | Complete |
| \`src/brain/orchestrator.py\` | 1.2 (updated 2.3, 3.1, Phase 4) | Complete (Phase 2 verify/replan + Phase 3 episodic replay + Phase 4 edit-learning wired in) |
| `src/brain/planner.py` | 1.2 (updated Phase 4) | Complete (HostedLLMPlanner + optional LocalPlanner) |
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 5 rule-table expansion + read-only guard) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete (review_and_learn wired to memory) |
| `src/action/playwright_driver.py` | 1.3 | Complete |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 | Complete |
| `src/confirmation/gate.py` | 1.4 | Complete |
| `src/confirmation/prompt_ui.py` | 1.4 | Complete |
| `src/observability/logger.py` | 1.5 (updated Phase 4) | Complete (LoopAudit + log_event, llm_call accuracy) |
| `src/observability/trace_replay.py` | 5 | Complete |
| \`src/perception/ocr.py\` | 2.1 | Complete |
| \`src/perception/element_detector.py\` | 2.1 | Complete |
| \`src/perception/screen_diff.py\` | 2.1 | Complete |
| `src/memory/episodic_store.py` | 3.1 (updated Phase 4) | Complete (edited flag + flagged_for_review) |
| `src/memory/semantic_store.py` | 3.2 | Complete |
| `src/memory/memory_api.py` | 3.2 (updated Phase 4) | Complete |
| `src/brain/research_router.py` | 4.1 | Complete |
| `tests/` | ongoing | In progress (121 tests passing: 16 Phase 1 + 35 Phase 2 + 24 Phase 3 + 22 Phase 4 + 24 Phase 5) |

## Known blockers
- Live end-to-end run (real screen capture, real Tesseract OCR, real mouse/keyboard control, real Gemini
  API call) not yet performed in this environment — 97 unit tests pass and all modules import cleanly, but
  a Windows display, the Tesseract binary, and a real `GEMINI_API_KEY` are required for a true live run,
  which is on the user's machine, not this build environment. Episodic replay's matching quality (the 0.82
  difflib threshold in `episodic_store.py`) and the new `corrections:<action>` semantic-memory namespace
  have only been validated against unit-test phrasing/edits — real usage logs from Phase 5 hardening may
  warrant retuning both. `LocalPlanner`/`build_http_generate_fn` are wired in but untested against a real
  local model server (no such server available in this build environment).

## Known gaps (honest remainder after the 2026-07-12 remediation pass)
This project underwent an independent line-by-line gap review, and every concretely fixable issue found
was fixed and tested (see `docs/DECISIONS.md` and `docs/DEBUG.md` entries dated 2026-07-12). What's
listed below is what remains, stated plainly rather than glossed over:

- **Zero live validation, still.** Every one of the 165 passing tests runs against mocks. No real
  Playwright browser, real Tesseract OCR, real mouse/keyboard, or real Gemini call has ever executed in
  this project's history. OCR accuracy, click-coordinate precision, `screen_diff.py`'s real-world false-
  positive/negative rate, and basic timing/race conditions are all genuinely unknown until run on real
  hardware.
- **The hard-boundary guard (`boundary_guard.py`) is still keyword/phrase-based**, same class of
  mechanism as `risk_classifier.py`. It is a real, independent, non-gateable second layer now (a
  meaningful improvement over relying on the planner LLM's own judgment alone), but it is not a
  guarantee — sufficiently novel phrasing, or a prompt-injection attack crafted specifically against its
  known phrase list, could still slip through. Closing this completely would require a fundamentally
  different mechanism (e.g. a dedicated classifier model), which is out of scope for this pass.
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
