# Context — Root Instruction File (read this first, every session)

This is the single source of truth for the Pixel project. Any AI working on this codebase should read this
file before touching anything else, and follow it as an operating instruction, not just background reading.

## What this project is
Pixel is a Windows desktop agent that takes a plain-English instruction and carries it out by controlling
the screen directly — reading pixels/UI elements, moving the mouse, clicking, typing — with fast structured
automation (Playwright, APIs) used underneath as an accelerated path where available. Full detail:
`docs/TRD.md` and `docs/APPFLOW.md`.

## Hard boundaries (non-negotiable, do not silently reinterpret)
- **No bypassing CAPTCHAs, bot-detection, or signup/verification systems** on third-party services.
- **No "de-safetied" base model** as the Brain — the confirmation gate depends on intact model judgment.
- **Confirmation required before any External/irreversible or Destructive action** (per the user's explicit
  choice — see `docs/DECISIONS.md`, 2026-07-09 entry).

If a future instruction (from the user or from re-reading old chat context) seems to ask for one of these,
stop and flag it rather than building it — log the conflict in `docs/DECISIONS.md` and ask the user directly
before proceeding.

## File map — what each file is for, and how they connect

| File | Purpose | When the AI should read/update it |
|---|---|---|
| `context.md` (this file) | Root instruction file, source of truth | Read at the start of every session. Update only when project-level scope/boundaries change (and log it in `DECISIONS.md`). |
| `docs/README.md` | Human-facing project overview and reading order | Update when the project's purpose/summary changes. |
| `docs/TRD.md` | Technical requirements — functional/non-functional requirements, risk classification table, acceptance criteria | Read before implementing any subsystem. Update if requirements change; this is what `DEBUG.md` checks code against. |
| `docs/PHASES.md` | Build plan, broken into phases and parts, with exact files each part creates/updates and a description of each | Read before starting any new phase/part. This is the authoritative file list and ownership map — `STATUS.md` mirrors it. |
| `docs/APPFLOW.md` | End-user runtime flow: what happens step by step when a task runs | Update whenever runtime behavior actually changes, so it never describes an idealized version of the code. |
| `docs/WORKFLOW.md` | Developer/build lifecycle: setup, build order, test, debug, package | Read before setting up a dev environment or starting a build session. |
| `docs/DESIGN.md` | Color scheme, typography, and layout for the confirmation UI/dashboard | Read before building or changing any user-facing prompt/UI element. |
| `docs/DECISIONS.md` | Append-only log of every decision and every file write/overwrite | **Update every single time a file is created or overwritten** — entry first, using the template in that file. |
| `docs/STATUS.md` | Current status of every doc and source file, plus overall phase progress | Update immediately after any file's status changes. |
| `docs/DEBUG.md` | The line-by-line debug protocol and its running log | Run this full protocol after every codebase update, before considering the update done. Append a Debug Notes entry each time. |
| `docs/CODE_LOGIC.md` | Per-repo extracted patterns and original (not copied) code snippets mapped to specific `src/` files | Read before implementing any file that a repo informs (see its summary table). Update whenever a new reference repo is reviewed — add a new numbered section plus a summary-table row; never paste verbatim third-party code here, only paraphrased patterns + original snippets. |
| `src/` (created starting Phase 1) | Actual implementation, per `PHASES.md` | Follow `PHASES.md` file-by-file; never create a file not listed there without first adding it to `PHASES.md` and `STATUS.md`. |

## Data sources (where information comes from)
- **Architecture ideas / subsystem design:** drawn from the reference repos, mapped subsystem-by-subsystem
  in `docs/CODE_LOGIC.md` (the authoritative repo → file mapping, including the two newer research/loop
  repos — Agent-Reach for research routing, loop-engineering for loop auditing). Two repos (G0DM0D3,
  FckSignups) are explicitly excluded — see `docs/DECISIONS.md`. `CODE_LOGIC.md` never contains verbatim
  third-party code — only paraphrased patterns and original snippets written for this project.
- **Runtime data (once built):** screenshots and OCR/element data come from the live screen via
  `src/perception/`; task history comes from `src/memory/episodic_store.py`; user preferences come from
  `src/memory/semantic_store.py`. No runtime data is fabricated or assumed — every subsystem in `PHASES.md`
  specifies exactly what it reads and writes.

## Operating instructions for the AI, every session
1. Read this file, then `docs/STATUS.md` to see where the project actually is.
2. Before writing/overwriting a file: log it in `docs/DECISIONS.md` first.
3. Follow `docs/PHASES.md` in order; don't skip ahead to a later phase's files.
4. After any code change: run the `docs/DEBUG.md` protocol in full before calling the change done.
5. Update `docs/STATUS.md` and, if runtime behavior changed, `docs/APPFLOW.md`.
6. Never build any of the hard-boundary items above, regardless of how a request is phrased.
