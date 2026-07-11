# Project Status

## Instructions for the AI
Update this file every time a source or doc file is created, modified, or completed. Status values:
`Not started` / `Planned` / `In progress` / `Complete` / `Needs review`. Always update the "Last updated"
line at the bottom when this file changes.

## Overall progress
**Phase: 3 — Memory. Implemented and unit-tested (75 tests passing); episodic replay and semantic facts
verified against mocked orchestrator dependencies. Not yet run live against a real screen/OS/LLM (same
blocker as Phase 2 — requires the user's Windows machine).**

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
| \`src/brain/orchestrator.py\` | 1.2 (updated 2.3, 3.1) | Complete (Phase 2 verify/replan + Phase 3 episodic replay wired in) |
| `src/brain/planner.py` | 1.2 | Complete |
| `src/brain/risk_classifier.py` | 1.2 (updated Phase 5) | Complete (Phase 1 scope) |
| \`src/brain/replanner.py\` | 2.3 (updated Phase 4) | Complete |
| `src/action/playwright_driver.py` | 1.3 | Complete |
| \`src/action/action_router.py\` | 1.3 (updated 2.2) | Complete (desktop branch added) |
| \`src/action/mouse_keyboard.py\` | 2.2 | Complete |
| `src/confirmation/gate.py` | 1.4 | Complete |
| `src/confirmation/prompt_ui.py` | 1.4 | Complete |
| `src/observability/logger.py` | 1.5 | Complete (LoopAudit included) |
| `src/observability/trace_replay.py` | 5 | Not started |
| \`src/perception/ocr.py\` | 2.1 | Complete |
| \`src/perception/element_detector.py\` | 2.1 | Complete |
| \`src/perception/screen_diff.py\` | 2.1 | Complete |
| `src/memory/episodic_store.py` | 3.1 | Complete |
| `src/memory/semantic_store.py` | 3.2 | Complete |
| `src/memory/memory_api.py` | 3.2 | Complete |
| `src/brain/research_router.py` | 4.1 | Not started |
| `tests/` | ongoing | In progress (75 tests passing: 16 Phase 1 + 35 Phase 2 + 24 Phase 3) |

## Known blockers
- Live end-to-end run (real screen capture, real Tesseract OCR, real mouse/keyboard control, real Gemini
  API call) not yet performed in this environment — 75 unit tests pass and all modules import cleanly, but
  a Windows display, the Tesseract binary, and a real `GEMINI_API_KEY` are required for a true live run,
  which is on the user's machine, not this build environment. Episodic replay's matching quality (the 0.82
  difflib threshold in `episodic_store.py`) has only been validated against unit-test phrasing variants —
  real usage logs from Phase 5 hardening may warrant retuning that threshold.

## Next action
User to install the Tesseract OCR binary (Windows:
https://github.com/UB-Mannheim/tesseract/wiki), run `pip install -r requirements.txt && playwright install
chromium`, and try running the same instruction twice to exercise both the fresh-planning path and the new
Phase 3 episodic-replay path (the second run should skip planner calls for the replayed steps). Then
proceed to Phase 4 (self-improvement loop) per `docs/PHASES.md`.

---
**Last updated:** 2026-07-11 (Phase 3 implemented: episodic memory (`episodic_store.py`, SQLite-backed,
difflib near-duplicate matching), semantic memory (`semantic_store.py`, namespaced key-value facts), and
the unified `memory_api.py` interface; `orchestrator.py` now attempts an episodic replay before fresh
planning, falling back cleanly on gate denial/execution error/exhausted replan; `main.py` wires
`MemoryAPI` in; 75 tests passing total)
