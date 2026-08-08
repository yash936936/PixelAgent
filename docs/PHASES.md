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

## Phase 6 — Live-wire the semantic risk layer
**Status: complete (2026-08-01)**

Goal: connect the semantic risk/boundary layer (`semantic_matcher.py`, `SemanticRiskJudge`,
`semantic_boundary_match` — added 2026-08-01, currently proven only via
`eval/adversarial_boundary_eval.py --model semantic`) to the actual live orchestrator, which has no path to
it at all today.

| File | Description |
|---|---|
| `src/config.py` (updated) | Add `"semantic"` as a valid `risk_model_backend` value alongside `"none"/"hosted"/"local"`. No new endpoint config needed — this backend is local/in-process, unlike `"local"`. |
| `src/main.py` (updated) | Add a branch in the risk-judge builder returning `SemanticRiskJudge().judge` when `cfg.risk_model_backend == "semantic"`. |
| `src/brain/orchestrator.py` (updated) | Wire `semantic_boundary_match()` into `_check_boundary()` as an explicit second, additive layer alongside `boundary_guard.check()` — log both verdicts, never let the semantic layer override the keyword layer's non-negotiable stop. |
| `docs/DECISIONS.md`, `docs/STATUS.md` | Record the wiring decision once shipped, same convention as every other change in this project. |

**Phase 6 success criterion:** a live task run with `RISK_MODEL_BACKEND=semantic` actually escalates a
paraphrased destructive/boundary step that the keyword-only baseline would have missed — verified by trace
log, not just the eval harness.

---

## Phase 7 — First real live validation (Windows)
**Status: COMPLETE (2026-08-02).** Both execution paths have now completed a full task on real Windows
hardware with zero errors and zero replans needed — the browser path earlier in this cycle, and the
desktop path confirmed clean on 2026-08-02 (`"open Notepad and type a test message"` → `status: done`, all
4 steps `executed`, 0 replans, 0 errors, replayed from a stable stored episode at $0.00 cost). This
satisfies the phase's own success criterion in full.

Nine distinct real bugs were found and fixed along the way, each root-caused from an actual trace rather
than guessed at, and each covered by a new regression test:
1. A transient truncated-JSON planner crash (now retried once before raising).
2. A planner/`action_router` schema mismatch (`selector` vs `target_text` for desktop clicks) — fixed in
   both the prompt and with a defensive fallback.
3. A safety-relevant confirmation-gate bug: unrecognized CLI input silently fell through to "approved."
4. A missing window-focus verification gap: a typed message landed in the terminal instead of the target
   app.
5. Stale episodic replay silently bypassing the planner (and thus bypassing fix #4) — closed with a
   `STEP_SCHEMA_VERSION` replay gate.
6. An unconditional Chrome launch blocking a purely desktop-only task that never used a browser — fixed by
   making Chrome launch lazily, plus two related gaps found where earlier fixes had only been wired into
   the CLI (`main.py`), never the GUI (`src/gui/worker.py`).
7. A Gemini 429 rate-limit crash, then its own fix's compounding backoff (10+ minutes of wait) — both
   fixed, the latter made fully configurable (`RATE_LIMIT_MAX_ATTEMPTS`/`RATE_LIMIT_MAX_BACKOFF_SECONDS`).
8. An undocumented `hotkey` action forcing the planner into a fragile OCR click on the Start button in
   every single trace — fixed by documenting it and recommending `{"keys": ["win"]}` explicitly.
9. A type-then-hotkey timing race (typing into Windows search immediately followed by Enter, before the
   search-results UI had populated) — fixed by giving `type_text()`/`press_hotkey()` the same post-action
   settle delay `click_at()` already had.

Full details for each are in `docs/DECISIONS.md`'s 2026-08-01/2026-08-02 entries.

**What Phase 7 does NOT cover, and remains open:** real Windows DPI/multi-monitor scaling (no run so far
has exercised non-100% display scaling); the `src/gui/worker.py` port of today's CLI-path fixes is
unverified in any environment (GUI tests require PySide6, unavailable in this build environment).

Goal (met): close the "zero live validation" gap that has been honestly flagged since Phase 5 — the
browser path was live-run-tested first (2026-07-13, profile-launch bug); the desktop path is now confirmed
clean as well (2026-08-02).

| File | Description |
|---|---|
| *(no new files — validation phase)* | First live run of the browser (Playwright) path on the user's real Windows machine, generating real `logs/task_*.jsonl` traces. |
| `src/action/mouse_keyboard.py` | First-ever live test of the desktop/OS-level mouse-keyboard path — a distinct code path from the browser branch, with genuinely zero real-world validation to date. |
| *(observation only)* | Real Windows DPI/multi-monitor scaling against OCR-derived click coordinates — the `tests/integration/` harness deliberately fixed viewport size to sidestep this, so it remains untested until now. |

**Phase 7 success criterion (MET, 2026-08-02):** one full task completes end-to-end on real Windows
hardware via each execution path (browser and desktop), with a real trace log to inspect for coordinate
drift, OCR misses, or timing issues that no mock could reveal.

---

## Phase 8 — Data security & retention
**Status: COMPLETE (2026-08-02).** Design decision recorded first, per this phase's own requirement (see
`docs/DECISIONS.md`'s 2026-08-02 entries for full reasoning): Windows DPAPI over a user-managed passphrase
or separately-stored symmetric key, since DPAPI ties encryption to the current Windows user account with
zero key file to manage, lose, or leak — the same mechanism Windows itself uses for saved Wi-Fi passwords.
Retention: trace logs/screenshots in `logs/` pruned once older than `LOG_RETENTION_DAYS` (default 14) at
process startup, not a background service.

| File | Description |
|---|---|
| `src/security/at_rest.py` (new) | Windows DPAPI wrapper (`protect`/`unprotect`/`is_available`) — degrades to plaintext with a one-time loud warning on non-Windows platforms, matching the existing `MouseKeyboard`/`OCREngine` graceful-degradation pattern. |
| `src/memory/semantic_store.py`, `episodic_store.py` (updated) | Sensitive columns (`instruction`, `normalized_instruction`, `steps_json`, `value_json`) encrypted via `at_rest.protect()` before every write, decrypted transparently on every read — `find_match()`'s difflib matching logic unaffected, since decryption happens immediately after fetch, before any comparison. |
| `src/observability/logger.py` (updated) | New `prune_old_logs(log_dir, retention_days)` — deletes `.jsonl`/`.png` files older than `retention_days`; `<= 0` disables pruning entirely rather than deleting everything. |
| `src/config.py` (updated) | New `log_retention_days` field (env `LOG_RETENTION_DAYS`, default 14). No toggle added for disabling encryption itself — no legitimate reason a user would want to turn off a transparent, free protection. |
| `src/main.py`, `src/gui/worker.py` (updated) | Both call `prune_old_logs()` once at startup — done together in the same pass this time, learning from Phase 7's earlier CLI/GUI-parity miss (`TESSERACT_CMD`/`AUTO_APPROVE_EXTERNAL` had only been wired into `main.py` initially). |
| `src/doctor.py` (updated) | New `check_encryption_at_rest()` — reports whether DPAPI is actually available, non-blocking either way. |

**Phase 8 success criterion (MET, 2026-08-02):** a documented, reviewed design decision (recorded in
`docs/DECISIONS.md`) for where keys live and how long screenshots/logs persist — before any live run
touches a real, personal Chrome profile with real account data.

**Not yet verified:** none of this has been exercised against real DPAPI — `pywin32` cannot be installed in
this project's Linux build/test environment, so every test uses a reversible fake standing in for
`win32crypt`. Confirm on a real Windows machine (after `pip install pywin32`) that `python -m src.doctor`
reports encryption as available, and that existing episodic/semantic memory continues to work correctly
after upgrading.

---

## Phase 9 — Injection-aware risk signal
**Status: COMPLETE (2026-08-02).** `boundary_guard.check_injection_signal()` scores every step's action/
description/param values against a phrase bank of common prompt-injection framings ("ignore previous
instructions", "disregard the user", "system:", etc.), independently of and never overriding
`risk_classifier.py`'s risk tiers or `check()`'s hard boundaries — deliberately never blocks, denies, or
halts a step by itself, since the success criterion below is about visibility, not gating.

| File | Description |
|---|---|
| `src/brain/boundary_guard.py` (updated) | New `check_injection_signal(step) -> InjectionSignal \| None`, kept deliberately separate from `check()` — a distinct signal for "planned step's rationale traces back to on-screen text that itself reads like an instruction," a different threat model (attacker-controlled webpage content) than ordinary risk classification. |
| `src/brain/orchestrator.py` (updated) | New `_check_injection_signal()`, called on every step in both the normal planning loop and the replay loop, logging a distinct `possible_prompt_injection_signal` trace event without affecting task execution. |
| `eval/adversarial_cases.jsonl` (updated) | New fifth category (`prompt_injection`, 6 cases, `adv_031`–`adv_036`) — independently written, since no real captured injection attempts exist yet (Phase 7's live runs were all legitimate benign tasks). |
| `eval/injection_signal_eval.py` (new) | Small dedicated scorer for the new category, kept separate from `adversarial_boundary_eval.py` since it scores a fundamentally different kind of output (a binary signal, not a risk/boundary verdict). 100% accuracy on its own case set. |

**Phase 9 success criterion (MET, 2026-08-02):** a step whose action originated from injected on-screen text
(not the user's own task description) is flagged distinctly in the trace log, even when its phrasing alone
wouldn't trip risk classification.

**Not fully solved, and honestly scoped as such:** this is a phrase-bank heuristic, the same class of tool
as `risk_classifier.py`'s original keyword-only floor — sufficiently novel injection phrasing could still
slip through undetected (a natural future extension would be a semantic-layer upgrade using the same
`semantic_matcher.py` machinery Phase 6 used for risk classification). It also only inspects a step's own
description/params — the planner's own paraphrase of what it read — not the actual raw on-screen page
content, which would need separate text-extraction-and-diffing plumbing not attempted here.

---

## Phase 10 — Track B data bootstrap (bridge to real training)
**Status: COMPLETE (2026-08-02), with an honest zero result.** Mining real Phase 7 trace data found two
real bugs in the mining infrastructure itself before it found any correction data (see
`docs/DECISIONS.md`'s matching entry) — both fixed. After fixing, the actual mined result across every
real trace available: zero denied gate decisions, zero edited gate decisions, zero genuine
unclassified-risk gaps. `semantic_matcher.py`'s exemplar banks were deliberately NOT modified, since there
is nothing real to inform a change yet.

| File | Description |
|---|---|
| `src/observability/trace_replay.py` (updated) | `unclassified_or_missing_risk()` fixed — was flagging terminal `"done"` steps and intermediate replan-retry log lines as false gaps against real data. Now excludes `done` actions and only considers the final logged entry per `step_num`. |
| `src/brain/orchestrator.py` (updated) | Fixed a related real bug found during the same investigation: risk was already classified before every step executed, but five error-path `log_step()` call sites never threaded it through, so every error-terminated step logged `risk: null` regardless of its actual tier. |
| `training/mine_corrections.py` (new) | The actual mining tool — combines `denied_gate_decisions()`, `edited_gate_decisions()`, and the fixed `unclassified_or_missing_risk()` into one scan. Deliberately never auto-modifies `semantic_matcher.py`; surfaces candidates for human review. Prints an honest "no candidates found" message rather than forcing a result. |
| `src/brain/semantic_matcher.py` | **Not updated** — no real correction data exists yet to inform a change. |
| `training/prepare_dataset.py`, `training/train_lora.py` | Still only runnable once enough real data exists and a real GPU machine is available — unchanged blocker, not resolved by this phase. |

**Phase 10 success criterion: NOT MET, explicitly and honestly.** `eval/adversarial_boundary_eval.py
--model semantic` shows no change, because no real-data-informed exemplars were added — there was nothing
real to inform them with. This is reported as the actual outcome of the phase, not worked around or
fabricated. `training/mine_corrections.py` is built, tested, and ready to surface real candidates
automatically the first time a user genuinely denies or edits a gate decision, or a step reaches a final
outcome with no risk classified.

---

## Phase 11 — Packaging & distribution
**Status: COMPLETE (2026-08-02).** Also a major, unplanned capability unlock: PySide6 turned out to
actually install and run in this project's Linux build environment (`pip install PySide6==6.11.1`), which
was not known to be possible before this phase. Every GUI test now runs and passes here — the full
395-test suite (347 non-GUI + 48 GUI) ran together in one pass for the first time in this project's
history, closing (going forward) the "GUI tests not re-verified in this environment" caveat that appeared
throughout every earlier phase's docs.

Goal: everything up to Phase 10 makes the agent safe and validated to run; nothing yet makes it installable
by anyone other than a developer running from source.

| File | Description |
|---|---|
| `pyproject.toml` (new) | Proper packaging metadata. **Actually built and verified**: `python -m build --wheel`, installed, confirmed `pixel`/`pixel-gui` console commands genuinely work — not just written and assumed correct. |
| `src/main.py` (updated) | New `cli_main()`, a zero-argument wrapper around `main(instruction)` for the `pixel` console entry point (`console_scripts` are invoked with no args). |
| `src/gui/app.py`, `src/gui/setup_wizard_logic.py` (new), `src/gui/widgets/setup_wizard.py` (new) | First-run setup wizard — closes a real gap where `config.load()` ran before `QApplication` even existed, so a fresh install with no `.env` crashed with a raw traceback before any window appeared. Logic (`needs_setup`, `looks_like_a_real_api_key`, `write_env_file`) kept Qt-free and fully unit-tested; the `QDialog` itself constructed and exercised offscreen with real PySide6. |
| `installer/pixel-agent.iss` (new) | Complete Inno Setup script — per-user install, optional Tesseract/Chromium components, pre-seeds `TESSERACT_CMD`. **Written per Inno Setup's documented syntax, NOT compiled** — `ISCC.exe` is a real Windows binary unavailable in this environment. |
| `docs/RELEASE.md` (new) | The real build/sign/release process, with an honest per-step verified/unverified table rather than one blanket claim. Code signing explicitly flagged as not set up at all (no certificate exists). |

**Phase 11 success criterion (MET for the software side, UNVERIFIED for the installer):** someone who
isn't the author can download one file, install it, and get to a working first task with no terminal/
source access. The `SetupWizard` genuinely closes the "no terminal access" gap for a person who already has
the app running — verified with real PySide6 in this environment. The "download one file" half of this
criterion depends on `installer/pixel-agent.iss` actually compiling and running correctly on a real Windows
machine, which has **not** been done — see `docs/RELEASE.md`'s verified/unverified table.

---

## Phase 12 — Docker deployment (browser-only mode)
**Status: COMPLETE (2026-08-02).** Goal: containerize the subset of PixelAgent that can genuinely run
headless on Linux. Real OS-level desktop automation (`mouse_keyboard.py`) fundamentally cannot run in a
headless Linux container — this phase scopes that limitation explicitly rather than pretending the whole
agent containerizes. See Phase 13 for the desktop-automation path.

| File | Description |
|---|---|
| `src/config.py`, `src/main.py`, `src/gui/worker.py` (updated — differs from original plan below) | New `execution_mode: "browser_only" \| "full_desktop"` config value, validated the same way `risk_model_backend` already is. Implemented at the desktop-backend-construction layer (`_build_desktop_backends()`) rather than in `action_router.py` as originally planned — this way the container never even attempts to construct `MouseKeyboard` at all (verified: a test asserts the mock is never called), rather than constructing it and then having `action_router.py` refuse to use it at execution time. Ported into `worker.py` in the same pass as `main.py`, learning from the earlier Phase 7/8 CLI/GUI-parity miss. |
| `Dockerfile` (new) | Base image with Python, the Tesseract binary, and Playwright's Chromium pre-installed (`playwright install --with-deps chromium`). **Not built in this environment** — no `docker` binary available here. |
| `docker-compose.yml` (new) | Wires up required `GEMINI_API_KEY` (compose refuses to start without it), `AUTO_APPROVE_EXTERNAL=true` by default (no interactive terminal inside a detached container — Destructive-risk steps remain unaffected regardless), named volumes for `logs/`/`profiles/` persistence across restarts. Default `command` runs a simple smoke-test task so `docker compose up` alone demonstrates real success, per the literal wording of the success criterion below. |
| `.dockerignore` (new) | Excludes `tests/`, `training/`, `docs/`, dev-only tooling from the build context. |
| `docs/DOCKER.md` (new) | States the browser-only limitation in its very first section. Includes a concrete 4-step smoke-test checklist — including a step that deliberately sends a desktop-targeting instruction to confirm `EXECUTION_MODE=browser_only` is actually enforced inside a running container, not just validated by the test suite in isolation. |

**Phase 12 success criterion (written correctly, UNVERIFIED — no Docker available in this build
environment):** a browser-only task runs successfully end-to-end inside the container from a fresh
`docker compose up`, with logs and memory persisting across a container restart, and the image clearly
documents (and the code enforces) that desktop-automation tasks are out of scope here. The code-side half
of this (enforcement) is genuinely tested and verified. The container-side half (an actual `docker compose
up` succeeding) has not been run — follow `docs/DOCKER.md`'s smoke-test checklist on a machine with Docker
installed before treating this deployment path as confirmed working.

---

## Phase 13 — Docker deployment (full desktop automation, via nested Windows VM)
Goal: the only way to genuinely containerize real desktop automation is to containerize a real Windows
machine — a Windows guest running inside a VM (QEMU/KVM) inside the container (the pattern the open-source
`dockur/windows` project uses), with PixelAgent installed normally inside that guest. This is materially
heavier than Phase 12 and deliberately its own phase.

| File | Description |
|---|---|
| `docker/windows-vm/Dockerfile` (new) | QEMU/KVM-based container running a real Windows guest — requires the Docker host to expose `/dev/kvm` (rules out most shared/serverless hosts; needs a dedicated VM or bare-metal server). |
| `docker/windows-vm/provision.ps1` (new) | Guest-side provisioning: installs Phase 11's Windows installer, Tesseract, Chrome, and Playwright dependencies inside the guest — PixelAgent runs natively inside the VM, not adapted for Linux. |
| `docker-compose.desktop.yml` (new) | Exposes the guest desktop via noVNC/RDP for human oversight (needed for the confirmation-gate UI, which needs a real display), mounts persistent volumes for the guest's Chrome profile, `logs/`, and memory stores. |
| `src/config.py` (updated) | Container-orchestration hooks — a thin HTTP API wrapping `orchestrator.run_task()`, since there's no host-side process to exec into for a nested VM the way there is for Phase 12's native Linux container. |
| `docker/windows-vm/reset-snapshot.sh` (new) | Clean-state reset between tasks/batches — snapshot-and-restore the guest so each run starts from known-clean Windows state rather than accumulating drift across unattended runs. |
| `docs/DOCKER_DESKTOP.md` (new) | Host requirements (nested virtualization support, realistic RAM/CPU/disk sizing for a full Windows guest) and the tradeoff this phase documents: this is genuinely running Windows, not emulating Windows automation on Linux, so it inherits Windows licensing and patching concerns as a real, separate OS instance. |

**Phase 13 success criterion:** a real desktop-automation task (one that specifically exercises
`mouse_keyboard.py` against a native Windows app, not a browser task) completes end-to-end inside the
VM-in-container deployment, controllable remotely via noVNC/RDP, with a clean guest-state reset available
between runs.

---

## Phase 14 — CI/CD & release engineering
| File | Description |
|---|---|
| `.github/workflows/test.yml` (new) | Every push runs the full non-GUI suite, GUI suite (offscreen Qt), and the adversarial eval — every test run in this project's history to date has been manual. |
| `.github/workflows/release.yml` (new) | Automated build of Phase 11's Windows installer and Phase 12/13's Docker images on tag push, with smoke tests for each. |
| `CHANGELOG.md` (new) | User-facing release notes, separate from `docs/DECISIONS.md`'s developer-facing append-only log. |
| Versioning scheme (semver) | Applied to the app itself and, separately, to any trained Track B model artifact — so a model regression can be rolled back independently of an app update. |

**Phase 14 success criterion:** a merge to main automatically produces a tested, installable build (native +
both Docker variants); a bad release can be rolled back without manual intervention.

---

## Phase 15 — Operational safety limits
| File | Description |
|---|---|
| `src/config.py` (updated) | Hard ceilings beyond `max_steps_per_task`: max cost per task, max concurrent tasks, per-task wall-clock timeout with forced termination. |
| `src/brain/orchestrator.py` (updated) | Enforce the above — currently `max_steps_per_task` exists but nothing stops a stuck/looping task on cost or wall-clock time. |
| `src/observability/logger.py` (updated) | Crash/hang detection — long-running-session stability (browser memory leaks, orphaned Playwright/Chromium processes) has never been tested past a single task. |
| Monitoring hook (new, e.g. lightweight local dashboard or opt-in telemetry) | Error rate, cost, and stuck-task visibility for a user running this unattended — currently only visible via manual trace-log inspection. |

**Phase 15 success criterion:** the agent survives a multi-hour stress run (repeated tasks back-to-back)
without a memory leak, orphaned process, or runaway cost, and self-terminates cleanly when a limit is hit.

---

## Phase 16 — Security review
| File | Description |
|---|---|
| *(review, not new code)* | Independent (ideally third-party, at minimum a fresh-eyes self-review) audit of the confirmation-gate/boundary-guard trust boundary — the eval harness's cases are a good regression suite, not a security audit. |
| `eval/adversarial_cases.jsonl` (expanded) | Grow well past the current case count using real red-team attempts, not just hand-written paraphrases. |
| Credential/secrets handling (review) | `.env`-based API key storage, Chrome profile access, and Phase 8's encryption-at-rest design all need a dedicated pass focused specifically on "what happens if this machine is compromised." |

**Phase 16 success criterion:** a documented security review exists, findings are triaged and either fixed
or explicitly accepted with reasoning recorded in `docs/DECISIONS.md`.

---

## Phase 17 — Legal & trust
| File | Description |
|---|---|
| `TERMS.md`, `PRIVACY.md` (new) | User-facing terms and a privacy policy covering what's logged, where, and for how long (depends on Phase 8's retention decision). |
| `docs/COMPLIANCE.md` (new) | Explicit review of target sites' Terms of Service re: automated access — a real liability question the moment this runs on behalf of anyone other than the original developer against their own accounts. |
| Audit trail for end users (updated `trace_replay.py` or new export) | The existing trace logs were built for developer debugging. A second party trusting this agent with their accounts needs a legible "what did it do, when, why" view — not raw JSONL. |

**Phase 17 success criterion:** a documented answer (not necessarily "yes it's fine everywhere") to "what
happens legally if this agent takes an action a site's ToS prohibits," and an audit trail an end user could
actually read.

---

## Phase 18 — Field testing / beta
| File | Description |
|---|---|
| *(process, not code)* | A small group of real users — people who are not the author, on hardware/configurations the author didn't set up — run this for real tasks over a real period of time. This is the only way to surface failure modes a single developer's supervised testing structurally cannot: unexpected site layouts, unusual DPI/monitor setups, edge-case account states. |
| Feedback/crash-report channel (new) | Some way for beta users to report a failure with enough context (trace log excerpt) to be actionable, without exposing their full screenshot history. |
| `docs/BETA_FINDINGS.md` (new) | Honest record of what broke during beta and what got fixed, same append-only spirit as `docs/DECISIONS.md`. |

**Phase 18 success criterion:** a defined number of beta users (even just 5–10) complete real tasks across a
real time window (e.g. two weeks) with no unrecoverable failures and no unrecovered-from safety-boundary
miss.

---

## Deployment readiness gate
"Production ready" means all of Phases 6–18 done, in order, with each phase's success criterion actually met
and recorded — not just "code exists." Phases 6–10 make the core safe to run at all; 11–13 make it
installable and operable across native Windows, browser-only Docker, and full-desktop Docker targets; 14–15
make it CI/CD-automated and operationally bounded; 16–17 make it security- and legal-sound to hand to someone
else; 18 is the only phase that proves any of the above holds up outside one developer's own supervised use.

---

## Explicitly deferred (not scheduled in any phase)
- Certification/exam auto-completion
- Signup/verification bypass
- Non-Windows platforms (Phase 12's browser-only Docker image runs on Linux, but that's a deployment
  target for the existing Windows-authored codebase, not a native non-Windows port)
- True multi-user/multi-tenant deployment (a single shared instance serving many independent users with
  isolation between them) — Phases 12–13 containerize a single-user instance for easier deployment, which is
  a different problem from multi-tenancy and remains unaddressed
