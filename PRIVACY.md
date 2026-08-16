# Privacy Policy

**Last updated: 2026-08-16 (Phase 17).**

This document describes what Pixel Agent stores, where, for how long, and who can read
it. It covers the software as distributed — a single-user Windows desktop agent you run
yourself, not a hosted service. There is no PixelAgent server; nothing described below
is transmitted to the project's author or to any third party except the two external
calls listed in "Third-party services" below.

## What gets stored, and where

Everything lives locally on your machine, under the app's data directory (by default,
next to the installed app or your source checkout — see `docs/WORKFLOW.md`). Nothing is
synced anywhere by the app itself.

| Data | Where | What it contains |
|---|---|---|
| Trace logs | `logs/task_*.jsonl` | A step-by-step record of each task: the instruction you gave, each planned action, its risk classification, whether you approved/denied/edited it, and the outcome. Sensitive-looking parameter values (matched by key name — password/token/secret/key/api_key-style fields) are redacted with `***REDACTED***` before being written; free-text fields like the instruction itself and step descriptions are **not** pattern-scanned and may contain anything you typed. |
| Screenshots | `logs/` (referenced by path from trace logs) | Full-frame captures taken at verification/gate points. These are the single highest-risk artifact this app produces — a screenshot captures whatever was on your screen at that moment, not just what the step's own parameters mention. |
| Episodic memory | `memory/episodic.db` | Past task instructions and their full step sequences, used to replay similar tasks faster next time. |
| Semantic memory | `memory/semantic.db` | Learned facts/preferences distilled from your corrections over time (e.g. "prefer X over Y"). |
| Configuration | `.env` | Your Gemini API key and runtime settings. **Stored in plaintext** — see "What is not encrypted" below. |
| Chrome profile | wherever you point `CHROME_PROFILE_PATH` | Whatever your browser profile already contains (cookies, saved logins, browsing history) — this app reuses your real profile rather than creating an isolated one, by design, so authenticated sites work. |

## Encryption at rest

On Windows, the `instruction`/`normalized_instruction`/`steps_json` columns in episodic
memory and the `value_json` column in semantic memory are encrypted using **Windows
DPAPI** (`CryptProtectData`/`CryptUnprotectData`) before being written to disk.

**What this actually protects against, stated precisely rather than just "encrypted":**
DPAPI ties the encryption to your specific Windows user account and machine. It protects
against (a) another local account on a shared machine reading these files without your
Windows login session, and (b) the drive later being lost, stolen, resold, or backed up
somewhere and read by someone without your Windows account's credentials.

**What it does not protect against:** DPAPI does not protect against an attacker who
already has your active Windows session (they can decrypt the same way the app does), a
fully remote attacker with an active session or admin rights on the machine, or anyone
reading process memory or watching your screen while the app runs. If someone has that
level of access, application-level encryption doesn't meaningfully help — no desktop
app's encryption-at-rest claim would.

**Non-Windows environments:** DPAPI is Windows-only. On any other OS, encryption is
unavailable and the app stores this data in plaintext, printing an explicit warning the
first time it does so rather than silently degrading.

## What is not encrypted

- **`.env`, including your `GEMINI_API_KEY`, is stored in plaintext.** This is a known,
  deliberately accepted gap (see `docs/DECISIONS.md`'s 2026-08-15 triage, Finding 2) — a
  real fix needs Windows Credential Manager integration and a config-loading redesign,
  scoped as its own future project rather than attempted here. In the meantime, a local
  pre-commit secret scanner (`detect-secrets`) is in place to stop this key from
  accidentally landing in a `git commit` if you fork or contribute to this project.
- **Trace logs and screenshots are not encrypted**, only pruned by age (below).
- **Redaction of sensitive parameters is keyword-based, not exhaustive.** Anything typed
  into a step's free-text `description`, or your original task instruction, is stored
  and logged as-is.

## Retention

Trace logs and screenshots under `logs/` are deleted once older than
`LOG_RETENTION_DAYS` (config value, default **14 days**). This check runs once at
process startup, not as a background service — the app isn't always running, so
startup-time pruning is the natural point to do it.

Episodic and semantic memory are **not** time-pruned — their entire purpose is to
persist so the app can replay similar tasks and remember learned preferences. If you
want to clear this data, delete `memory/episodic.db` and `memory/semantic.db` directly;
there is currently no in-app "clear my data" command (a reasonable future addition, not
yet built).

## Third-party services

- **Google Gemini API** — every planning/risk-classification call sends the current
  task instruction, recent step history, and (for vision-based verification) a
  screenshot to Google's Gemini API, governed by [Google's own API terms and privacy
  policy](https://ai.google.dev/gemini-api/terms). This is unavoidable — Gemini is how
  the agent decides what to do next.
- **Whatever site or app you point the agent at** — if you ask it to interact with a
  website or application, that site/app receives whatever normal interaction (clicks,
  typed text, page loads) any browser/user would produce. This app does not add any
  additional tracking beyond what your normal use of that site already involves. See
  `docs/COMPLIANCE.md` for the separate question of whether a given site's own Terms of
  Service permit this kind of automated interaction at all.

No data is sent to the author of this project. There is no telemetry, analytics, or
crash-reporting call in this codebase as of this writing.

## Your choices

- Set `LOG_RETENTION_DAYS` lower (or to `0`, if supported by your version — check
  `src/config.py`) to reduce how long trace logs/screenshots persist.
- Delete `memory/episodic.db` / `memory/semantic.db` to clear learned history.
- Use `EXECUTION_MODE=browser_only` (Phase 12) if you don't want the agent to have
  desktop-level mouse/keyboard control at all.
- The confirmation gate (see `TERMS.md`) means the agent will not take an
  External-risk or Destructive-risk action without asking you first, by default.

## Changes to this policy

This is a living document, updated as the project's data-handling behavior actually
changes (per `context.md`'s operating instructions — this file is updated whenever
runtime behavior affecting stored data changes, and every such change is logged in
`docs/DECISIONS.md`).
