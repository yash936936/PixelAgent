# Build Phases

Reference file tree (created incrementally across phases):

```
pixel-agent/
├── context.md
├── docs/ (this folder)
├── src/
│   ├── main.py
│   ├── config.py
│   ├── brain/
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   ├── risk_classifier.py
│   │   └── replanner.py
│   ├── memory/
│   │   ├── episodic_store.py
│   │   ├── semantic_store.py
│   │   └── memory_api.py
│   ├── perception/
│   │   ├── ocr.py
│   │   ├── element_detector.py
│   │   └── screen_diff.py
│   ├── action/
│   │   ├── mouse_keyboard.py
│   │   ├── playwright_driver.py
│   │   └── action_router.py
│   ├── confirmation/
│   │   ├── gate.py
│   │   └── prompt_ui.py
│   └── observability/
│       ├── logger.py
│       └── trace_replay.py
├── tests/
└── requirements.txt
```

---

## Phase 0 — Foundations
**Status: complete (this documentation set)**

Files handled: all files in `docs/` and `context.md`.

No source code yet. Success criterion: architecture, scope, and safety model agreed before any code is
written.

---

## Phase 1 — Minimal loop, browser only
Goal: prove the Brain → Action → Confirmation loop works end-to-end for browser-only tasks, before adding
pixel perception complexity.

### Part 1.1 — Skeleton & config
| File | Description |
|---|---|
| `src/main.py` | Entry point. Accepts a natural-language instruction (CLI arg for v1), initializes config, Brain, Action, Confirmation, and Observability, and runs the task loop. |
| `src/config.py` | Loads settings: LLM API key/model, default Chrome profile, max-step budget, log directory. Single source of config truth — every other module reads from here, nothing hardcodes config elsewhere. |
| `requirements.txt` | Pinned dependencies: `playwright`, LLM SDK, logging libs. |

### Part 1.2 — Brain (planning only, no memory/perception yet)
| File | Description |
|---|---|
| `src/brain/orchestrator.py` | The main loop: observe → plan next step → act → verify → repeat. Calls `planner.py` for step generation and `risk_classifier.py` before every action. Enforces the max-step budget from `config.py`. |
| `src/brain/planner.py` | Turns the NL instruction (+ current screen/page state) into the next single step (not the whole plan up front — steps are generated incrementally so the Brain can react to actual page state). |
| `src/brain/risk_classifier.py` | Implements the risk table from `TRD.md §5`. Classifies a proposed step as Local/External/Destructive using rule-based keyword matching first, LLM judgment as fallback for ambiguous cases. |

### Part 1.3 — Action (Playwright only)
| File | Description |
|---|---|
| `src/action/playwright_driver.py` | Wraps Playwright: launch with a named Chrome profile, navigate, click by selector/text, type, screenshot. This is the only Action file touched in Phase 1 — `mouse_keyboard.py` doesn't exist yet. |
| `src/action/action_router.py` | Routes a Brain-issued step to the right executor. In Phase 1 it only ever routes to `playwright_driver.py`; the branch for pixel-level control is added in Phase 2. |

### Part 1.4 — Confirmation gate
| File | Description |
|---|---|
| `src/confirmation/gate.py` | Given a classified step, blocks execution for External/Destructive until an approval decision is received. Records the decision. |
| `src/confirmation/prompt_ui.py` | Minimal CLI/console prompt for v1: shows the proposed action, screenshot path, target account/profile, and Approve/Deny/Edit options. |

### Part 1.5 — Observability
| File | Description |
|---|---|
| `src/observability/logger.py` | Structured logger: every plan, action, screenshot reference, gate decision, and outcome, with timestamps, written to the local log directory from `config.py`. |

**Phase 1 success criterion:** reliably complete "open Chrome profile → navigate → click/type → confirm"
tasks end to end, with every External step correctly gated.

---

## Phase 2 — Pixel perception + desktop control
Goal: extend beyond browser-only tasks to arbitrary desktop applications.

### Part 2.1 — Perception
| File | Description |
|---|---|
| `src/perception/ocr.py` | Runs OCR over a screenshot, returns text + bounding boxes. |
| `src/perception/element_detector.py` | Detects clickable UI elements (buttons, fields, links) and their bounding boxes, so the Brain can target "the Submit button" instead of raw coordinates. |
| `src/perception/screen_diff.py` | Compares before/after screenshots to verify a step had the expected effect; feeds `brain/replanner.py`. |

### Part 2.2 — Action (desktop control)
| File | Description |
|---|---|
| `src/action/mouse_keyboard.py` | Raw OS-level mouse move/click/drag and keyboard input, for apps with no DOM/API path. |
| `src/action/action_router.py` (updated) | Adds the pixel-control branch: prefers `playwright_driver.py` when the target is a web page, falls back to `mouse_keyboard.py` otherwise. |

### Part 2.3 — Brain (replanning)
| File | Description |
|---|---|
| `src/brain/replanner.py` | Triggered when `screen_diff.py` shows an action didn't produce the expected state; asks the planner for a corrected next step instead of blindly continuing. |
| `src/brain/orchestrator.py` (updated) | Wires in the verify step using `screen_diff.py` and calls `replanner.py` on mismatch. |

**Phase 2 success criterion:** a task that requires a non-browser desktop app (e.g. a native settings
dialog) completes correctly using pixel control, with Playwright still preferred for web pages.

---

## Phase 3 — Memory
### Part 3.1 — Episodic memory
| File | Description |
|---|---|
| `src/memory/episodic_store.py` | Persists (instruction, step plan, outcome, timestamp) per completed task. Provides a lookup for "have I done something like this before?" |
| `src/brain/orchestrator.py` (updated) | Before planning fresh, checks `episodic_store.py` for a matching past task and attempts replay; falls back to fresh planning if replay fails. |

### Part 3.2 — Semantic memory
| File | Description |
|---|---|
| `src/memory/semantic_store.py` | Durable key-value facts: user preferences (e.g. default Chrome profile), learned UI quirks per site/app. |
| `src/memory/memory_api.py` | Unified read/write interface both stores go through, so orchestrator/planner never touch storage directly. |

**Phase 3 success criterion:** repeating a previously successful task is measurably faster (fewer LLM
planning calls) and at least as reliable as the first run.

---

## Phase 4 — Self-improvement loop
| File | Description |
|---|---|
| `src/brain/replanner.py` (updated) | Extended to also learn from user-edited confirmation-gate approvals — if the user edits a proposed action before approving, that correction is written back to `semantic_store.py`. |
| `src/memory/episodic_store.py` (updated) | Adds a review pass that flags failed/edited tasks for the improvement loop to inspect. |

Optional: local fine-tuned planning model swap-in for `brain/planner.py` for routine steps (cheaper than a
hosted LLM call every time), added as a config option in `config.py`, never replacing the Brain's safety
behavior (per `TRD.md §6`).

### Part 4.1 — Research routing (added after reviewing Agent-Reach; see `docs/CODE_LOGIC.md §7`)
| File | Description |
|---|---|
| `src/brain/research_router.py` | New file. Registers available research tools (web search, GitHub API, etc.) and routes a query to the right one by platform, with a `doctor()` health-check method. Used when a task requires looking something up (e.g. "find repo X") before acting on it. Does not include cookie-based login automation for third-party social platforms — that would cross into the signup/verification boundary in `TRD.md §6`. |

### Part 4.2 — Loop auditing (added after reviewing loop-engineering; see `docs/CODE_LOGIC.md §9`)
| File | Description |
|---|---|
| `src/observability/logger.py` (updated) | Adds a `LoopAudit` helper tracking step count, LLM call count, and estimated cost per task, surfaced alongside the existing trace log. Directly supports the max-step budget requirement in `TRD.md §3.1`. |

**Phase 4 success criterion:** measurable drop in repeated user corrections for the same task type over
time.

---

## Phase 5 — Hardening
| File | Description |
|---|---|
| `src/brain/risk_classifier.py` (updated) | Rule table expanded from real usage logs collected in Phases 1–4. |
| `src/observability/trace_replay.py` | New file: lets a developer step through a full past task trace (plan, screenshots, gate decisions) for debugging. |

**Phase 5 success criterion:** no unclassified/misclassified risk cases observed in a full regression pass
over logged tasks; full trace replay works for any logged task.

---

## Explicitly deferred (not scheduled in any phase)
- Certification/exam auto-completion
- Signup/verification bypass
- Multi-user or cloud-hosted deployment
- Non-Windows platforms
