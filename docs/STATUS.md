# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 4 — Self-improvement loop. Implemented and unit-tested (97 tests passing); user-edit learning,
review-flagging, research routing, and loop-audit accuracy all verified against mocked dependencies. Not
yet run live against a real screen/OS/LLM (same blocker as Phases 2-3 — requires the user's Windows
machine).**

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
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 1 scope) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete (review_and_learn wired to memory) |
| `src/action/playwright_driver.py` | 1.3 | Complete |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 | Complete |
| `src/confirmation/gate.py` | 1.4 | Complete |
| `src/confirmation/prompt_ui.py` | 1.4 | Complete |
| `src/observability/logger.py` | 1.5 (updated Phase 4) | Complete (LoopAudit + log_event, llm_call accuracy) |
| `src/observability/trace_replay.py` | 5 | Not started |
| \`src/perception/ocr.py\` | 2.1 | Complete |
| \`src/perception/element_detector.py\` | 2.1 | Complete |
| \`src/perception/screen_diff.py\` | 2.1 | Complete |
| `src/memory/episodic_store.py` | 3.1 (updated Phase 4) | Complete (edited flag + flagged_for_review) |
| `src/memory/semantic_store.py` | 3.2 | Complete |
| `src/memory/memory_api.py` | 3.2 (updated Phase 4) | Complete |
| `src/brain/research_router.py` | 4.1 | Complete |
| `tests/` | ongoing | In progress (97 tests passing: 16 Phase 1 + 35 Phase 2 + 24 Phase 3 + 22 Phase 4) |

## Known blockers
- Live end-to-end run (real screen capture, real Tesseract OCR, real mouse/keyboard control, real Gemini
  API call) not yet performed in this environment — 97 unit tests pass and all modules import cleanly, but
  a Windows display, the Tesseract binary, and a real `GEMINI_API_KEY` are required for a true live run,
  which is on the user's machine, not this build environment. Episodic replay's matching quality (the 0.82
  difflib threshold in `episodic_store.py`) and the new `corrections:<action>` semantic-memory namespace
  have only been validated against unit-test phrasing/edits — real usage logs from Phase 5 hardening may
  warrant retuning both. `LocalPlanner`/`build_http_generate_fn` are wired in but untested against a real
  local model server (no such server available in this build environment).

## Next action
User to install the Tesseract OCR binary (Windows:
https://github.com/UB-Mannheim/tesseract/wiki), run `pip install -r requirements.txt && playwright install
chromium`, and exercise: (1) a fresh task, (2) the same task repeated (Phase 3 replay), and (3) a task where
a confirmation-gate step is edited before approving (Phase 4 review_and_learn — check
`logs/semantic_memory.db` for a new `corrections:<action>` fact afterward). Then proceed to Phase 5
(hardening: `risk_classifier.py` rule-table expansion + `trace_replay.py`) per `docs/PHASES.md`.

---
**Last updated:** 2026-07-11 (Phase 4 implemented: `research_router.py` (new, Part 4.1), `replanner.py`'s
`review_and_learn()` wired to semantic memory, `episodic_store.py`/`memory_api.py` gained an `edited` flag
and `flagged_for_review()`, `orchestrator.py` now learns from user-edited gate approvals in both the
fresh-planning and replay paths, `logger.py` gained `log_event()` and an accurate `llm_call` flag on
`log_step()` so LoopAudit reflects real planner-call savings, and `planner.py`/`config.py`/`main.py` gained
an optional local-planner backend swap-in; 97 tests passing total)
