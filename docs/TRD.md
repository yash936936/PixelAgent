# Technical Requirements Document (TRD)

## 1. Purpose
Defines what must be true for Pixel to be considered correctly built at each stage. This is the reference
the debug pass (`DEBUG.md`) checks the codebase against.

## 2. Platform & environment
- OS: Windows 10/11 desktop
- Runtime: local process, single user, no multi-tenant/cloud requirement for v1
- Browser automation: Chromium/Chrome via Playwright
- LLM: hosted API (Gemini, free-tier eligible) for the Brain by default; local fine-tuned model is an optional Phase 4 swap-in

## 3. Subsystems and functional requirements

### 3.1 Brain (Orchestrator)
- MUST decompose a natural-language task into an ordered step list before executing anything
- MUST classify every step's risk level (Local/External/Destructive) before execution — see `TRD.md §5`
- MUST re-plan when a step's post-condition doesn't match the expected screen state
- MUST enforce a max-step budget per task (default 40 steps) to prevent runaway loops
- MUST NOT execute an External or Destructive step without a resolved confirmation-gate approval

### 3.2 Memory
- Episodic store: every completed task logged as (instruction, step plan, outcome, timestamp)
- Semantic store: durable key-value facts (user preferences, learned UI quirks) queryable by the Brain
- MUST be able to replay a previously successful plan for a near-identical repeat instruction
- MUST invalidate a cached plan if replay fails (screen state doesn't match) and fall back to fresh planning

### 3.3 Perception
- MUST convert a raw screenshot into structured elements (text via OCR, clickable regions via UI element
  detection) before the Brain reasons over it
- MUST support screen-diffing to verify an action had the expected effect

### 3.4 Action
- MUST support: mouse move/click/drag, keyboard input, scroll — for arbitrary desktop apps
- MUST prefer Playwright (DOM-level) actions over raw pixel clicks whenever the target is a web page
- MUST fall back to pixel-level control when no structured path exists

### 3.5 Observability
- MUST log every plan, action, screenshot reference, and outcome with a timestamp
- MUST log every confirmation-gate decision (proposed/approved/denied/edited)
- MUST support replaying a full task trace for debugging

## 4. Non-functional requirements
- No plaintext storage of user credentials
- All logs stored locally by default
- Agent must be interruptible mid-task (user can cancel at any confirmation prompt)

## 5. Risk classification (authoritative table)

| Class | Definition | Gate behavior |
|---|---|---|
| Local, reversible | Only affects local UI state | Auto-execute, log only |
| External / irreversible | Visible to other people/systems, or hard to undo | Block, require explicit user approval |
| Destructive | Deletes/overwrites user data | Block, require approval + re-typed confirmation phrase |

## 6. Hard boundaries (non-configurable)
- No autonomous completion of graded coursework, exams, or certifications
- No bypassing CAPTCHA/bot-detection/signup-verification systems on third-party services
- Brain MUST run on a model with intact safety training — no "de-safetied" base model swap

## 7. Acceptance criteria by phase
See `PHASES.md` — each phase lists its own success criterion and the files it introduces or modifies.
