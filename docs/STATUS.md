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

## Next action
User to install the Tesseract OCR binary (Windows:
https://github.com/UB-Mannheim/tesseract/wiki), run `pip install -r requirements.txt && playwright install
chromium`, and exercise the full live loop (Phases 1-5), including running a real task end to end to
generate a real `logs/task_*.jsonl` trace, then pointing `python -m src.observability.trace_replay` at it
(or the `logs/` dir) to confirm live-trace replay and check for any `unclassified_or_missing_risk()` gaps
that only real usage would surface. Per Phase 5's success criterion, run a full regression pass over
accumulated logged tasks looking for misclassified risk cases and feed any misses back into
`risk_classifier.py`'s keyword tables (with a new `DECISIONS.md` entry per change).

---
**Last updated:** 2026-07-11 (Phase 5 implemented: `risk_classifier.py` rule table expanded — Destructive
keywords: format/wipe drives, clear history, account deletion, subscription cancellation, branch/repo
deletion, hard reset, etc.; External keywords: DMs/invites, issue/PR actions, bookings/orders, account
linking/authorization, etc. — plus a read-only-guard check to avoid overclassifying steps that only
inspect a sensitive element; `trace_replay.py` created (new, Part 5) with forward/backward/jump stepping,
gate-decision and missing-risk queries, screenshot listing, and a minimal CLI; 121 tests passing total,
24 new for Phase 5)
