# Decisions Log

This file is a running, append-only history of every decision made about the project — including every time
the AI writes a new file or overwrites an existing one. Nothing is deleted from this file; corrections are
made by adding a new dated entry, not editing old ones.

## Instructions for the AI (read every session)
- Before writing or overwriting **any** file in this project, add an entry here first (or immediately after,
  same turn) describing: what changed, why, and what it affects.
- Every entry MUST use the template below. No free-form entries.
- If a decision reverses or modifies a prior entry, reference the prior entry's date/title instead of
  silently contradicting it.
- Scope/safety-boundary decisions (see `context.md` hard boundaries) can be referenced but never silently
  overridden — a hard boundary can only change if the user explicitly asks in-session, and that request
  itself gets its own logged entry here before anything downstream changes.

## Entry template
```
### [YYYY-MM-DD] Title
- **Type:** New file / Overwrite / Design decision / Scope change
- **File(s) affected:** path(s)
- **What changed:**
- **Why:**
- **Impacts:** (which other files/docs need review as a result — check STATUS.md)
```

---

## Log

### [2026-07-09] Initial architecture decided
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/PHASES.md`
- **What changed:** Chose pixel-first control as the default execution path, with Playwright/API calls as
  an accelerated path underneath, rather than API-only automation.
- **Why:** Generalizes to apps/sites with no API (course platforms, internal tools, legacy desktop apps),
  matching the user's requirement to handle "any task I can perform on the laptop."
- **Impacts:** `PHASES.md` Phase 1/2 split (browser-first, then desktop pixel control).

### [2026-07-09] Excluded certification/exam auto-completion
- **Type:** Scope change
- **File(s) affected:** `context.md`, `docs/TRD.md`
- **What changed:** Removed "complete certification courses for me" from the feature set entirely.
- **Why:** Autonomous completion of graded coursework/exams misrepresents who actually earned the
  credential — this is credential fraud regardless of framing.
- **Impacts:** No repo mapped to this feature; excluded permanently per `TRD.md §6` hard boundaries.

### [2026-07-09] Excluded signup/verification bypass (FckSignups) and de-safetied model (G0DM0D3)
- **Type:** Scope change
- **File(s) affected:** `context.md`, `docs/TRD.md`
- **What changed:** Both repos removed from the feature/repo mapping.
- **Why:** FckSignups is built to defeat CAPTCHA/bot-detection/verification gates on third-party services —
  conflicts with acting as the user's honest agent rather than an abuse tool. G0DM0D3 is built to strip a
  model's safety training, which would break the confirmation-gate behavior the whole safety model depends
  on.
- **Impacts:** `TRD.md §6` hard boundaries; `docs/PHASES.md` never schedules either capability.

### [2026-07-09] Confirmation gate: approval required before irreversible/external actions
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/APPFLOW.md`, `docs/WORKFLOW.md`
- **What changed:** User selected "ask for confirmation before any irreversible/external action" over full
  autonomy or sensitive-only confirmation.
- **Why:** Explicit user choice.
- **Impacts:** `TRD.md §5` risk classification table; `src/confirmation/gate.py` design in `PHASES.md` Part
  1.4.

### [2026-07-09] Reviewed all 19 reference repos, created docs/CODE_LOGIC.md
- **Type:** New file
- **File(s) affected:** `docs/CODE_LOGIC.md` (new), `context.md` (file map + data sources sections),
  `docs/PHASES.md` (Phase 4 gained Parts 4.1 and 4.2), `docs/STATUS.md` (rows added)
- **What changed:** Went through every listed repo (including the 9 newly added since the prior session:
  ponytail, Agent-Reach, q-agent-harness, loop-engineering, pipecat, plus re-confirmation of
  TencentDB-Agent-Memory, cognee, PixelRAG, OpenManus, G0DM0D3, gbrain, OpenSpace, PraisonAI, Scrapling,
  openhuman, Playwright, playwright-mcp, langfuse, FckSignups, page-agent, UI-TARS-desktop, agent-browser,
  code-review-graph) and documented, per repo: what it does, the pattern extracted, and an original (not
  copied) code snippet mapped to a specific file in our `src/` tree. Two new `PHASES.md` additions
  resulted: `src/brain/research_router.py` (Phase 4, from Agent-Reach) and a `LoopAudit` addition to
  `src/observability/logger.py` (Phase 4, from loop-engineering).
- **Why:** User requested a full pass to extract core logic/patterns from every repo and centralize it as a
  build reference, without reproducing any repo's actual copyrighted source code verbatim.
- **Impacts:** `PHASES.md` Phase 4 scope grew (Parts 4.1/4.2); `STATUS.md` source-file table gained
  `research_router.py`; `context.md` file map and data-sources section now point to `CODE_LOGIC.md` as the
  authoritative repo mapping instead of an inline summary. G0DM0D3 and FckSignups re-confirmed excluded,
  consistent with the prior entries below — no reversal.

### [2026-07-09] Platform target: Windows desktop for v1
- **Type:** Design decision
- **File(s) affected:** `docs/TRD.md`, `docs/PHASES.md`
- **What changed:** User selected Windows desktop over macOS or cross-platform for v1.
- **Why:** Explicit user choice; cross-platform deferred to Phase 5+.
- **Impacts:** `PHASES.md` Phase 5 "revisit cross-platform support."
