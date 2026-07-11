# Pixel — Autonomous Desktop Agent

Pixel is a Windows desktop agent that takes a plain-English instruction and carries it out the way a human
would: reading the screen, moving the mouse, clicking, typing, and navigating browsers/apps — with a
confirmation gate before anything irreversible or externally visible happens.

## What it does
Give it a task like "open my Work Chrome profile, find repo X on GitHub, and star it" and it plans the
steps, executes them (via fast structured automation where possible, raw pixel control where not), asks you
to approve any external/irreversible step, and remembers how it did the task so repeats are faster.

## What it deliberately does not do
- Bypass CAPTCHAs, bot-detection, or signup/verification systems on other services

See `docs/DECISIONS.md` for why, and `../context.md` for the full project map.

## Where to start reading
1. `../context.md` — root instruction file, read this first (always up to date, agent's source of truth)
2. `docs/TRD.md` — technical requirements and subsystem design
3. `docs/PHASES.md` — build plan, broken into parts, with per-file ownership
4. `docs/APPFLOW.md` — runtime, user-facing flow
5. `docs/WORKFLOW.md` — developer/build lifecycle
6. `docs/DESIGN.md` — visual/UI design system for the agent's own interface (confirmation prompts, dashboard)
7. `docs/STATUS.md` — current progress per file
8. `docs/DECISIONS.md` — running log of every decision and file overwrite
9. `docs/DEBUG.md` — the debugging protocol run after every codebase update

## Platform
Windows desktop, single user, local-first. See `docs/PHASES.md` for the phased build order.
