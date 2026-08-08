# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 12 — Docker deployment (browser-only mode), COMPLETE (2026-08-02). Phase 11's installer is now
ALSO fully verified end-to-end on real Windows hardware (2026-08-08) — see update below.** Phases 1–5
complete; native Windows GUI added 2026-07-12; Phase 6 (semantic layer live-wired) complete 2026-08-01;
Phase 7 (first real live validation) complete 2026-08-02 — both browser and desktop paths completed a task
end-to-end with zero errors after nine real bugs found and fixed; Phase 8 (encryption-at-rest + log
retention) complete and confirmed working on the user's real Windows machine; Phase 9 (injection-aware,
non-blocking risk signal) complete; Phase 10 (Track B data bootstrap) complete with an honest zero result;
Phase 11 (packaging & distribution) complete in code as of 2026-08-02, and as of **2026-08-08 the actual
installer has now been built, installed, run, and uninstalled on real Windows hardware** — closing the
"nothing in installer/ has been run on a real Windows machine" caveat that persisted through every earlier
entry. Full reasoning for all in `docs/DECISIONS.md`'s 2026-08-01/2026-08-08 entries.

**Phase 12**: new `EXECUTION_MODE` config value (`full_desktop` default, or `browser_only`) — when
`browser_only`, `main.py`/`worker.py` skip even attempting to construct `MouseKeyboard`, verified with a
test asserting it's never called at all, not just that the result degrades to `None`. `Dockerfile`/
`docker-compose.yml`/`docs/DOCKER.md` (all new) define the actual browser-only container — **not built or
run in this environment**, since no `docker` binary is available here; written correctly per Docker's
documented syntax, still unverified until run on a real machine with Docker installed, per
`docs/DOCKER.md`'s own smoke-test checklist. Unchanged by this update.

Non-GUI suite: 195 → 354 tests passing; GUI suite: 0 → 48 tests passing (both now runnable in this
environment as of Phase 11) — full details in `docs/DECISIONS.md`'s 2026-08-02 Phase 11/12 entries.
**Still open:** real Windows DPI/multi-monitor scaling unverified; `Dockerfile`/`docker-compose.yml`'s
build/run steps still not executed on a real machine; Phase 9's injection signal remains a phrase-bank
heuristic; Phase 10's success criterion remains unmet (no real correction data exists yet); Phase 13
(nested-Windows-VM Docker, for real desktop automation) remains unbuilt; **`config.py`'s `llm_model`
default and `.env.example` still reference the now-deprecated `gemini-2.5-flash` — a real, source-level gap
found 2026-08-08, not yet fixed at the source (see that update below and
`PATCH_config_and_env_example.md`)**; a desktop-target-type task has not yet been confirmed from the
*installed* (packaged) build specifically, only from a source-run app. Next up: fix the `llm_model` default
at the source, then either Phase 13 (Docker deployment, full desktop automation via nested Windows VM) or
Phase 14 (CI/CD & release engineering) — see `docs/PHASES.md` for the full roadmap order.

## Documentation files (`docs/` + root)

| File | Status | Notes |
|---|---|---|
| `context.md` | Complete | Root instruction file |
| `docs/README.md` | Complete | |
| `docs/PHASES.md` | Complete | Defines full file tree ahead of implementation; Phase 11 entry updated 2026-08-08 to reflect real installer verification |
| `docs/DECISIONS.md` | Complete (ongoing) | Append-only, updated every future file change; 2026-08-08 entry added for the first full real-hardware installer build/install/run/uninstall cycle |
| `docs/STATUS.md` | Complete (ongoing) | This file |
| `docs/DESIGN.md` | Complete | Visual design system for confirmation UI/dashboard |
| `docs/TRD.md` | Complete | |
| `docs/APPFLOW.md` | Complete | |
| `docs/WORKFLOW.md` | Complete | |
| `docs/RELEASE.md` | **Updated (2026-08-08)** | Now genuinely verified end-to-end on real Windows hardware — PyInstaller bundling, Inno Setup compile, install/SetupWizard/uninstall, and a real browser-target-type task from the *installed* build are all `[VERIFIED]`. Five real bugs found and fixed this pass, documented in a new "Known issues found on first real build" section. Code signing still not set up. |
| `docs/DOCKER.md` | Complete (Phase 12, 2026-08-02) | Browser-only limitation stated upfront; a 4-step smoke-test checklist to actually run once Docker is available — nothing in it has been executed in this build environment (no `docker` binary here). Unchanged by this update. |
| `pyproject.toml` | Complete (Phase 11, 2026-08-02) | Actually built into a wheel and installed in this environment — `pixel`/`pixel-gui` console commands confirmed working, not just written |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Written, unverified (Phase 12, 2026-08-02) | Browser-only deployment — no `docker` binary available in this build environment, so nothing here has been built or run. Unchanged by this update. |
| `installer/pixel-agent.iss` | **Verified (2026-08-08)** | Complete Inno Setup script, now built and confirmed working end-to-end on real Windows hardware — `SourceDir`/`OutputDir` path fixes (2026-08-06), the `pixel-gui.exe` naming fix, and a new `PLAYWRIGHT_BROWSERS_PATH` env-seeding fix in `[Code]` (both 2026-08-08) are all applied and confirmed. Still cannot be *compiled* in this Linux build environment (`ISCC.exe` is Windows-only) — only ever built/tested on the user's real machine. |
| `docs/DEBUG.md` | Complete | |
| `docs/CODE_LOGIC.md` | Complete | Covers all 19 reviewed repos incl. 2 exclusions; adds `research_router.py` and `LoopAudit` to Phase 4 in `PHASES.md` |
| `docs/PHASE_7_CHECKLIST.md` | Complete (2026-08-01) | Step-by-step guide for the user's own Phase 7 live run — not executable/verifiable from this build environment |

## Source files (`src/`) — not yet created

| File | Phase | Status |
|---|---|---|
| `src/main.py` | 1.1 (updated Phase 6, 2026-08-01, Phase 11/12, 2026-08-02) | Complete (`_build_risk_model_judge` adds `"semantic"` branch — no endpoint needed; `cli_main()` added for the `pixel` console entry point; `_build_desktop_backends()` respects `EXECUTION_MODE=browser_only`, verified never to call `MouseKeyboard` in that mode) |
| `src/config.py` | 1.1 (updated Phase 6, 2026-08-01, Phase 8/12, 2026-08-02) | **Needs review (2026-08-08)** — `risk_model_backend` accepts `"semantic"`; `log_retention_days` and `execution_mode` added; but `llm_model`'s hardcoded default (`"gemini-2.5-flash"`, line 168) is now a dead model per Google's own deprecation notices — every fresh install inherits a 404 on its first task until this default is changed. Not yet fixed at the source; see `PATCH_config_and_env_example.md` for the exact one-line edit. |
| `src/doctor.py` | Phase 7 prep (2026-08-01), updated Phase 8 (2026-08-02) | Complete — pre-flight diagnostic (`python -m src.doctor`), checks Tesseract/Playwright/config/writable-dirs/semantic-layer/encryption-at-rest without executing a real task. Not a substitute for Phase 7 itself. Consider adding a live model-availability check here too, given the `llm_model` gap found 2026-08-08 — not yet added. |
| `requirements.txt` | 1.1 | Complete |
| \`src/brain/orchestrator.py\` | 1.2 (updated 2.3, 3.1, Phase 4, Phase 6, Phase 9) | Complete (Phase 2 verify/replan + Phase 3 episodic replay + Phase 4 edit-learning + Phase 6 always-on semantic boundary layer + Phase 9 non-blocking injection-signal check, both wired in) |
| \`src/brain/boundary_guard.py\` | 1.0 (updated Phase 6, Phase 9) | Complete (hard-boundary `check()` + Phase 9's non-blocking `check_injection_signal()`, deliberately kept separate) |
| `src/brain/planner.py` | 1.2 (updated Phase 4) | Complete (HostedLLMPlanner + optional LocalPlanner) |
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 5 rule-table expansion + read-only guard) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete (review_and_learn wired to memory) |
| `src/action/playwright_driver.py` | 1.3 (updated 2026-08-01) | Complete (fixed real profile-launch bug found via live GUI run, 2026-07-13; made Chrome launch lazy — `is_launched` property — after a desktop-only live task was needlessly blocked by a Chrome launch failure). **Note (2026-08-08):** the *bundled* (PyInstaller) build's missing-Chromium crash was not a bug in this file — it was a packaging/environment gap, fixed in `installer/pixel-agent.iss` instead (see `PLAYWRIGHT_BROWSERS_PATH` fix). |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 (updated 2026-08-01, 2026-08-02) | Complete (real focus-verification + periodic active-reactivation before typing + post-action settle delay on type/hotkey, all found/fixed via Phase 7 live runs). **Not yet re-confirmed against the installed (packaged) build** — Phase 7's desktop-path validation was against a source-run app. |
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
| `src/gui/app.py` | GUI (2026-07-12, updated Phase 11, 2026-08-02) | Complete — shows `SetupWizard` before `config.load()` when no usable `.env` exists. **Confirmed working on a genuinely clean install (2026-08-08)** — an earlier test that appeared to skip the wizard was traced to a leftover `.env` from prior testing, not a real bug. |
| `src/gui/setup_wizard_logic.py` | Phase 11 (2026-08-02) | Complete — pure logic (no Qt import) backing the first-run wizard: `needs_setup()`, `looks_like_a_real_api_key()`, `write_env_file()`. Fully unit-tested without a display. **Gap noted 2026-08-08:** the wizard collects the Gemini API key and Chrome profile, but has no field for `LLM_MODEL` — every install silently inherits `config.py`'s hardcoded (currently dead) default with no in-wizard way to override it. Worth a follow-up: either add a model field to the wizard, or fix the default and accept that power users edit `.env` by hand for anything else. |
| `src/gui/widgets/setup_wizard.py` | Phase 11 (2026-08-02) | Complete — the actual `QDialog`, UI plumbing only. Constructed and exercised offscreen; all interactions (button enable/disable, `.env` writing) verified with real PySide6 in this build environment. |
| `src/gui/main_window.py` | GUI (2026-07-12) | Complete (full dashboard: composer + trace + stats + memory) |
| `src/gui/worker.py` | GUI (2026-07-12, updated 2026-08-01, 2026-08-02) | Complete (background QThread + cross-thread confirmation bridge; `TESSERACT_CMD`/`auto_approve_external`/`execution_mode` all wired in, the last two ported in the same pass as `main.py` this time rather than found missing later. Now runnable/verified in this build environment — PySide6 installs here as of Phase 11.) |
| `src/gui/gui_logger.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/task_composer.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/trace_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/stats_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/memory_panel.py` | GUI (2026-07-12) | Complete |
| `src/gui/widgets/confirmation_dialog.py` | GUI (2026-07-12) | Complete |
| `requirements-gui.txt` | GUI (2026-07-12) | Complete (separate from requirements.txt, PySide6 only) |
| `tests/` | ongoing | In progress. Non-GUI: 354 passing — see prior entries for the full breakdown. **No new tests added 2026-08-08** — tonight's fixes were all in `installer/pixel-agent.iss` (not exercised by the Python test suite) and a manual `.env` workaround for `llm_model` (the real fix, changing `config.py`'s default, has not yet been made or tested — see the `src/config.py` row above). |
| `tests/integration/` | Improvement pass (2026-08-01) | New — offline real-pixel harness: real headless Chromium + real Tesseract + real `screen_diff`, no mocks. Requires Playwright's Chromium install + Tesseract binary; `pytest --ignore=tests/integration` to skip, same convention as `tests/gui/` |

## Known blockers
- Live end-to-end run (real screen capture, real Tesseract OCR, real mouse/keyboard control, real Gemini
  API call) — **now performed multiple times on the user's real Windows machine, both from source (Phase 7)
  and, as of 2026-08-08, from the packaged installer build** for the browser path specifically. The desktop
  path has been confirmed from source but not yet re-confirmed from the installed build. Episodic replay's
  matching quality (the 0.82 difflib threshold in `episodic_store.py`) and the `corrections:<action>`
  semantic-memory namespace remain validated only against unit-test phrasing/edits and Phase 7's small
  number of real traces. `LocalPlanner`/`build_http_generate_fn` remain untested against a real local model
  server.

## Known gaps (honest remainder)
This project underwent an independent line-by-line gap review, and every concretely fixable issue found
was fixed and tested (see `docs/DECISIONS.md` and `docs/DEBUG.md` entries dated 2026-07-12). What's
listed below is what remains, stated plainly rather than glossed over:

- **`config.py`'s `llm_model` default is a dead model (2026-08-08, new).** `"gemini-2.5-flash"` now
  returns a hard 404 for new API callers per Google's own deprecation schedule. Worked around on one
  installed machine by hand-editing that machine's `.env`; not yet fixed at the source. Every fresh
  install (including anyone else who downloads the installer) will hit this exact same 404 on their very
  first task until `config.py`'s default and `.env.example` are both updated. This is a real, currently
  live gap, not a hypothetical one — see `PATCH_config_and_env_example.md` for the fix.
- **Zero live validation against real OS DPI/multi-monitor scaling — still true.** Unchanged by tonight's
  packaging work.
- **The hard-boundary guard (`boundary_guard.py`) is still keyword/phrase-based as its primary mechanism**,
  with an additive semantic layer (Phase 6) — unchanged by this update.
- **Screenshots and logs are encrypted at rest on Windows (Phase 8, confirmed working)**, but full-frame
  screenshots can still contain arbitrary on-screen sensitive content — unchanged by this update.
- **No multi-user / concurrency model.** Unchanged.
- **The "no de-safetied base model" boundary is enforced by review process, not runtime code.** Unchanged.
- **The LLM risk-judge fallback costs an extra LLM call per ambiguous step and can be confidently wrong
  with no built-in way to distinguish that from a correct verdict without human review.** Unchanged.
- **A desktop-target-type task has not yet been confirmed from the installed (packaged) build specifically
  (2026-08-08, new)** — only a browser-target-type task has been run from `installer/`'s output so far;
  Phase 7's desktop-path testing predates the installer work and was against a source-run app.

## Track B: trained-model architecture
Unchanged by tonight's update — see prior entries. Two separate trained-model interfaces exist, both
disabled by default. Current keyword-only baseline: ~40% overall eval accuracy. Semantic layer (Phase 6,
live-wired): 73% overall. Neither satisfies the deployment gate in `eval/README.md`; nothing may be set to
`RISK_MODEL_BACKEND=local` until a real model is trained, evaluated, and documented per that file's
checklist.

## Next action
1. **Fix `config.py`'s `llm_model` default and `.env.example` at the source** (see
   `PATCH_config_and_env_example.md`) — this is now the single highest-priority small fix, since it's a
   live, reproducible bug that will hit every future install, not a hypothetical gap.
2. Rebuild the installer with the updated `installer/pixel-agent.iss` (already includes the
   `PLAYWRIGHT_BROWSERS_PATH` fix) and confirm a *fresh* install runs a browser task with zero manual
   `.env` patching required — the real proof tonight's fix is baked into the build process, not just this
   one machine.
3. Once that's confirmed, decide between Phase 13 (nested-Windows-VM Docker for real desktop automation)
   or Phase 14 (CI/CD & release engineering) per `docs/PHASES.md`'s roadmap order — not strictly forced,
   pick based on what's actually useful next.
4. Longer-standing, unchanged: mine real corrections into Track B's training pipeline once enough live
   usage exists; confirm the desktop path from the installed build specifically, not just from source.

---
**Last updated:** 2026-08-08 (First real Windows installer build/install/run/uninstall cycle completed
end-to-end. Five real bugs found and fixed: wrong `README.md` source path, `OutputDir` still resolving one
directory too high after an incomplete first fix, PyInstaller `--name` not matching `pixel-agent.iss`'s
`MyAppExeName` — producing a "successful" build with a broken Start Menu shortcut, PyInstaller's bundled
Playwright having no Chromium of its own — fixed by seeding `PLAYWRIGHT_BROWSERS_PATH` into the generated
`.env` via `pixel-agent.iss`'s existing `[Code]` section, and a dead `gemini-2.5-flash` default in
`config.py`/`.env.example` — worked around on the one installed machine, not yet fixed at the source.
`docs/RELEASE.md`'s verified/unverified table now shows Phase 11's installer as genuinely `[VERIFIED]`
end-to-end for the browser path, including a real completed task from the packaged build. See
`docs/DECISIONS.md`'s 2026-08-08 entry for full detail. Not yet done: fixing `llm_model`'s default at the
source, and confirming a desktop-target-type task from the installed build specifically.)

---
*(All entries prior to 2026-08-08 are preserved unchanged below/above per this file's own history — see
the original file for the full record from Phase 1 through Phase 12.)*
