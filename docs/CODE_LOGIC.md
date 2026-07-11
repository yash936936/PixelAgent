# Code Logic — Extracted Patterns From Reference Repos

**Important note on how this file was built:** GitHub repos are other people's copyrighted source code.
This file does not paste verbatim code from any of the repos below — instead, for each one it (a) states
what the repo actually does, (b) extracts the *pattern/technique* in plain language, and (c) gives an
**original**, written-from-scratch snippet showing how that pattern applies inside our `src/` tree (file
paths match `PHASES.md`). If you want the literal source, clone the repo directly — this doc is the design
bridge from "what they do" to "what we build," not a copy of their code.

---

## 1. DietrichGebert/ponytail — AI coding discipline (not a runtime subsystem)
**What it is:** A prompt/skill ruleset that pushes an AI coding agent toward the smallest correct
implementation — check if the task is needed at all, reuse existing code, prefer stdlib/native features,
avoid new dependencies, minimize line count — with intensity levels (lite/full/ultra).

**Pattern to take:** Not code for `src/` — this is a *process* rule for whichever AI is implementing
`PHASES.md`. Adopt it as a standing instruction.

**Applied to us:** Added to `docs/WORKFLOW.md` step 3 — "Build order" — as a coding-discipline rule: before
implementing any file in `PHASES.md`, check whether an existing dependency (Playwright, the LLM SDK, stdlib)
already solves it before writing custom code.

---

## 2. TencentCloud/TencentDB-Agent-Memory & topoteretes/cognee — Memory
**What they do:** TencentDB-Agent-Memory provides managed storage/retrieval for agent memory records
(short-term working memory separated from long-term storage). Cognee builds a knowledge graph over
memory — entities and relationships, not just a flat log — so memory is queryable ("what do I know about
X's UI").

**Pattern to take:** Two-tier storage (episodic log + semantic key-facts) with the semantic tier modeled as
light graph edges (task → UI-pattern → outcome), not just key-value.

**Original snippet — `src/memory/memory_api.py`:**
```python
# Original code for this project — not copied from either repo.
from dataclasses import dataclass
from typing import Any

@dataclass
class MemoryRecord:
    kind: str          # "episodic" | "semantic"
    subject: str        # e.g. "task:star_repo" or "ui_pattern:github_star_button"
    data: dict[str, Any]
    linked_to: list[str] | None = None   # graph-style links to other subjects

class MemoryAPI:
    def __init__(self, episodic_store, semantic_store):
        self._episodic = episodic_store
        self._semantic = semantic_store

    def remember_task(self, instruction: str, steps: list[dict], outcome: str) -> None:
        self._episodic.write(MemoryRecord(
            kind="episodic", subject=instruction,
            data={"steps": steps, "outcome": outcome},
        ))

    def learn_fact(self, subject: str, fact: dict, linked_to: list[str] | None = None) -> None:
        self._semantic.write(MemoryRecord(
            kind="semantic", subject=subject, data=fact, linked_to=linked_to,
        ))

    def recall_similar_task(self, instruction: str) -> MemoryRecord | None:
        return self._episodic.find_closest(instruction)
```

---

## 3. StarTrail-org/PixelRAG — Screen perception grounding
**What it does:** Grounds an LLM's reasoning in screen pixels via retrieval — instead of feeding a whole
screenshot into the prompt, it indexes screen regions and retrieves only the relevant ones for the current
sub-goal.

**Pattern to take:** Region-retrieval over full-screenshot dumping — cheaper and more targeted.

**Original snippet — `src/perception/element_detector.py`:**
```python
# Original code for this project — not copied from PixelRAG.
from dataclasses import dataclass

@dataclass
class ScreenRegion:
    text: str
    bbox: tuple[int, int, int, int]
    kind: str   # "button" | "field" | "link" | "text"

def find_relevant_regions(regions: list[ScreenRegion], goal_keywords: list[str]) -> list[ScreenRegion]:
    """Retrieve only the regions relevant to the current sub-goal instead of
    handing the Brain every detected element on screen."""
    goal_keywords = [k.lower() for k in goal_keywords]
    return [r for r in regions if any(k in r.text.lower() for k in goal_keywords)]
```

---

## 4. FoundationAgents/OpenManus — Local LLM training reference
**What it does:** Framework for training/fine-tuning a local agent-planning model as an alternative to a
hosted LLM.

**Pattern to take:** Not used until Phase 4 (per `PHASES.md`) — the interface for swapping planner backends
should be decided now so it's cheap to add later.

**Original snippet — `src/brain/planner.py` (interface, not full implementation):**
```python
# Original code for this project — not copied from OpenManus.
from abc import ABC, abstractmethod

class PlannerBackend(ABC):
    @abstractmethod
    def next_step(self, instruction: str, screen_state: dict, history: list[dict]) -> dict:
        ...

class HostedLLMPlanner(PlannerBackend):
    """Default for Phases 1-3: calls the hosted LLM API."""
    ...

class LocalFineTunedPlanner(PlannerBackend):
    """Phase 4 optional swap-in, trained per OpenManus-style pipeline, same interface."""
    ...
```

---

## 5. elder-plinius/G0DM0D3 — EXCLUDED
Purpose is stripping a model's safety training. Not used anywhere in this project. See `docs/DECISIONS.md`
(2026-07-09 entry) and `TRD.md §6`.

---

## 6. garrytan/gbrain — Orchestrator loop reference
**What it does:** Central LLM-driven agent loop: observe → plan → act → verify.

**Pattern to take:** This is the exact loop shape `brain/orchestrator.py` already uses (see `APPFLOW.md`).

**Original snippet — `src/brain/orchestrator.py` (core loop shape):**
```python
# Original code for this project — not copied from gbrain.
def run_task(instruction: str, max_steps: int = 40):
    history = []
    for _ in range(max_steps):
        screen_state = perceive()
        step = planner.next_step(instruction, screen_state, history)
        if step["type"] == "done":
            break
        risk = risk_classifier.classify(step)
        if risk in ("external", "destructive"):
            decision = confirmation_gate.request_approval(step, risk)
            if decision != "approved":
                logger.log_gate_decision(step, decision)
                break
        outcome = action_router.execute(step)
        if not screen_diff.matches_expected(outcome, step):
            step = replanner.correct(step, outcome, screen_state)
        history.append({"step": step, "outcome": outcome})
        logger.log_step(step, outcome)
    memory_api.remember_task(instruction, history, outcome="done")
```

---

## 7. Panniantong/Agent-Reach — Online search / multi-platform reading
**What it does:** A capability layer that installs, health-checks, and routes to existing upstream CLIs/MCP
tools (Twitter, Reddit, YouTube, GitHub, RSS, web search via Exa/Jina) rather than re-implementing readers
for each platform itself.

**Pattern to take:** "Router over a capability registry" — don't hardcode one search backend; register
available tools and route by platform, with a health-check (`doctor`) step.

**Original snippet — `src/brain/planner.py` support module (new addition, `src/brain/research_router.py`,
add to Phase 4's optional tooling in `PHASES.md`):**
```python
# Original code for this project — not copied from Agent-Reach.
class ResearchRouter:
    def __init__(self, available_tools: dict[str, callable]):
        self.tools = available_tools   # e.g. {"web_search": ..., "github_api": ...}

    def doctor(self) -> dict[str, bool]:
        return {name: self._health_check(tool) for name, tool in self.tools.items()}

    def route(self, platform: str, query: str):
        if platform not in self.tools:
            raise ValueError(f"No research tool registered for {platform}")
        return self.tools[platform](query)
```
Note: this is for the agent's own *research* tasks (e.g. "find repo X"), not a bulk social-media
scraping feature — cookie-based login automation for third-party platforms is out of scope per the same
signup/verification boundary in `TRD.md §6`.

---

## 8. kju4q/q-agent-harness & tinyhumansai/openhuman — Harness reference
**What they do:** Overall runtime harness tying subsystems (skills, memory, security checks, tool routing)
together around a coding/research agent.

**Pattern to take:** `src/main.py` should be a thin harness — wire subsystems together, no business logic
of its own.

**Original snippet — `src/main.py` shape:**
```python
# Original code for this project — not copied from either repo.
def main(instruction: str):
    cfg = config.load()
    memory = MemoryAPI(EpisodicStore(cfg), SemanticStore(cfg))
    gate = ConfirmationGate(prompt_ui)
    orchestrator = Orchestrator(planner=HostedLLMPlanner(cfg), memory=memory,
                                 gate=gate, logger=Logger(cfg))
    orchestrator.run_task(instruction)
```

---

## 9. cobusgreyling/loop-engineering — Agent loop design patterns
**What it does:** Patterns and CLI tools (`loop-audit`, `loop-init`, `loop-cost`) for designing and
auditing agent loops — cost tracking, loop initialization templates, auditing for runaway/inefficient
loops.

**Pattern to take:** Add loop auditing (step count, cost per task) to Observability, not just success/fail
logging.

**Original snippet — `src/observability/logger.py` addition:**
```python
# Original code for this project — not copied from loop-engineering.
class LoopAudit:
    def __init__(self):
        self.step_count = 0
        self.llm_calls = 0
        self.est_cost = 0.0

    def record_step(self, llm_call: bool, cost: float = 0.0):
        self.step_count += 1
        if llm_call:
            self.llm_calls += 1
            self.est_cost += cost

    def summary(self) -> dict:
        return {"steps": self.step_count, "llm_calls": self.llm_calls, "est_cost": self.est_cost}
```
This directly informs the max-step budget and cost visibility called for in `TRD.md §3.1`.

---

## 10. pipecat-ai/pipecat — Conversational/voice feature
**What it does:** Framework for real-time voice/conversational AI pipelines (speech-to-text, LLM, text-to-
speech, turn-taking).

**Pattern to take:** If a voice interface is added later (not in current `PHASES.md`), it plugs in as an
alternate front-end to `src/main.py` — the instruction still enters as text after speech-to-text, so it
doesn't change `brain/`, `action/`, or `confirmation/` at all.

**Original snippet — potential future `src/frontend/voice_input.py` (not scheduled in any current phase):**
```python
# Original code for this project — not copied from pipecat. Illustrative only, not in current PHASES.md.
def voice_to_instruction(audio_stream) -> str:
    text = speech_to_text(audio_stream)   # pipecat-style STT pipeline
    return text   # hands off to the same main(instruction) entry point
```
Add to `PHASES.md` as a new Phase 6 if/when prioritized — not added automatically here since it wasn't in
the original scope.

---

## 11. HKUDS/OpenSpace & MervinPraison/PraisonAI — Self-improvement
**What they do:** OpenSpace: an agent evaluates and revises its own past executions. PraisonAI: multi-agent
reflection loops where one agent critiques another's output.

**Pattern to take:** A lightweight critic pass over failed/edited tasks (already scheduled as Phase 4 in
`PHASES.md`).

**Original snippet — `src/brain/replanner.py` addition:**
```python
# Original code for this project — not copied from either repo.
def review_and_learn(failed_or_edited_task: dict, semantic_store):
    """Called from Phase 4's self-improvement loop. Compares the original
    proposed step to what the user actually approved/edited, and writes
    the correction as a semantic fact for next time."""
    if failed_or_edited_task.get("user_edit"):
        semantic_store.write_fact(
            subject=failed_or_edited_task["task_type"],
            fact={"correction": failed_or_edited_task["user_edit"]},
        )
```

---

## 12. D4Vinci/Scrapling — Research scraping (dev-time only)
**What it does:** Fast, resilient web scraping library (handles dynamic content, anti-bot page structure
changes better than basic requests+BeautifulSoup).

**Pattern to take:** Used only during *our own* development to pull documentation while building —
never shipped as a runtime capability of the agent itself (per `docs/DECISIONS.md`, this was already
decided). No `src/` file corresponds to this; it's a dev-tooling dependency only, referenced in
`docs/WORKFLOW.md` if we need to re-scrape reference docs during development.

---

## 13. microsoft/playwright & microsoft/playwright-mcp — Browser automation backend
**What they do:** Playwright: cross-browser automation library (launch, navigate, click by selector, type,
screenshot). playwright-mcp: exposes Playwright actions as MCP tools for an LLM agent to call directly.

**Pattern to take:** This is the literal dependency for `src/action/playwright_driver.py` — not just a
pattern reference, it's actually installed and imported (`pip install playwright`, already listed in
`PHASES.md` Part 1.1's `requirements.txt`).

**Original snippet — `src/action/playwright_driver.py` shape (using the real Playwright API, which is the
public library interface, not a copy of its internals):**
```python
# Uses the public Playwright API directly — this is how the library is meant to be called, not copied code.
from playwright.sync_api import sync_playwright

class PlaywrightDriver:
    def __init__(self, profile_name: str):
        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=f"./profiles/{profile_name}", headless=False,
        )
        self._page = self._context.new_page()

    def navigate(self, url: str):
        self._page.goto(url)

    def click(self, selector: str):
        self._page.click(selector)

    def type_text(self, selector: str, text: str):
        self._page.fill(selector, text)

    def screenshot(self, path: str):
        self._page.screenshot(path=path)
```
Consider using `playwright-mcp` directly as the MCP tool surface for the Brain instead of hand-rolling this
wrapper, once an MCP-based tool-calling setup is in place — evaluate at Phase 1 implementation time.

---

## 14. langfuse/langfuse — LLM observability
**What it does:** Tracing/observability platform for LLM calls — traces, spans, cost tracking, prompt
versioning.

**Pattern to take:** Use as the actual backend for `src/observability/logger.py` (real dependency, not just
inspiration) — wrap Brain LLM calls in Langfuse spans so plan/act/verify steps are traced with cost and
latency, not just written to a flat file.

**Original snippet — `src/observability/logger.py` shape:**
```python
# Original wiring code — uses the public Langfuse client, not copied internals.
from langfuse import Langfuse

class Logger:
    def __init__(self, cfg):
        self._lf = Langfuse(public_key=cfg.langfuse_public_key, secret_key=cfg.langfuse_secret_key)

    def log_step(self, step: dict, outcome: dict):
        with self._lf.start_span(name=step["type"]) as span:
            span.update(input=step, output=outcome)
```

---

## 15. BraveOPotato/FckSignups — EXCLUDED
Purpose is defeating signup/verification/anti-bot gates. Not used anywhere. See `docs/DECISIONS.md`
(2026-07-09 entry) and `TRD.md §6`.

---

## 16. alibaba/page-agent — Web-page-aware browsing
**What it does:** Agent reasoning that's aware of page structure (DOM hierarchy, semantic regions) rather
than treating a page as flat text/pixels.

**Pattern to take:** When routed through Playwright (structured path), prefer querying DOM structure over
OCR — only fall back to pixel/OCR perception when no DOM access exists (native desktop apps).

**Applied to us:** Refines the routing rule already in `TRD.md §3.4` — `action_router.py` should query page
structure via Playwright's own DOM APIs first, and only hand off to `perception/ocr.py` when the target
isn't a web page at all.

---

## 17. bytedance/UI-TARS-desktop — Desktop GUI control reference
**What it does:** GUI grounding + desktop control — closest existing analog to this whole project (vision
model interprets a desktop screenshot, decides on an action, executes mouse/keyboard control).

**Pattern to take:** The overall observe → interpret screenshot → decide action → execute loop for
non-browser desktop apps — this is the direct reference for `src/perception/` + `src/action/mouse_keyboard.py`
working together in Phase 2.

**Original snippet — `src/action/action_router.py` desktop branch:**
```python
# Original code for this project — not copied from UI-TARS-desktop.
def route_step(step: dict, playwright_driver, mouse_keyboard):
    if step["target_type"] == "web":
        return playwright_driver.execute(step)
    elif step["target_type"] == "desktop":
        regions = element_detector.detect(perceive_screen())
        target = find_relevant_regions(regions, step["target_keywords"])
        return mouse_keyboard.click(target[0].bbox) if target else None
```

---

## 18. vercel-labs/agent-browser — Browser automation CLI
**What it does:** Lightweight CLI-driven browser automation interface.

**Pattern to take:** Useful as a dev/debug tool for manually driving the same browser automation the agent
uses, for testing `action/playwright_driver.py` in isolation. Referenced in `docs/WORKFLOW.md` as an
optional dev-tooling aid, not a runtime dependency.

---

## 19. tirth8205/code-review-graph — Codebase intelligence graph
**What it does:** Builds a local, persistent graph of a codebase (functions, tests, call edges) so an AI
coding tool queries only the relevant slice instead of reading every file — large token savings on
large-repo review/debug tasks.

**Pattern to take:** Directly useful for our own `docs/DEBUG.md` protocol once `src/` grows past a handful
of files — instead of the AI re-reading the whole tree on every debug pass, build a graph once and query it
for "what does this file touch."

**Applied to us:** Added as a recommended dev-tool in `docs/WORKFLOW.md` and `docs/DEBUG.md` for Phase 3+
when the codebase is large enough that whole-tree reads get expensive — not required for Phase 1–2's small
file count.

---

## Summary table — repo → project file(s) it informs

| Repo | Primary file(s) affected |
|---|---|
| ponytail | `docs/WORKFLOW.md` (process rule only) |
| TencentDB-Agent-Memory, cognee | `src/memory/memory_api.py`, `episodic_store.py`, `semantic_store.py` |
| PixelRAG | `src/perception/element_detector.py` |
| OpenManus | `src/brain/planner.py` (backend interface) |
| G0DM0D3 | Excluded — none |
| gbrain | `src/brain/orchestrator.py` |
| Agent-Reach | `src/brain/research_router.py` (new, optional Phase 4 addition) |
| q-agent-harness, openhuman | `src/main.py` |
| loop-engineering | `src/observability/logger.py` (LoopAudit) |
| pipecat | Future optional Phase 6 (`src/frontend/voice_input.py`) — not currently scheduled |
| OpenSpace, PraisonAI | `src/brain/replanner.py` (Phase 4 review_and_learn) |
| Scrapling | Dev-tooling only, no `src/` file |
| Playwright, playwright-mcp | `src/action/playwright_driver.py` (real dependency) |
| langfuse | `src/observability/logger.py` (real dependency) |
| FckSignups | Excluded — none |
| page-agent | `src/action/action_router.py` (routing rule refinement) |
| UI-TARS-desktop | `src/action/action_router.py`, `src/action/mouse_keyboard.py` |
| agent-browser | Dev-tooling only, no `src/` file |
| code-review-graph | `docs/DEBUG.md`, `docs/WORKFLOW.md` (dev-tooling, Phase 3+) |
