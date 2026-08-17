# Beta Testing Guide

Thanks for testing Pixel Agent. This is a short, practical guide — how to report
something that goes wrong, and what to expect while you're using it.

## Before you start

- Read `TERMS.md` and `PRIVACY.md` — they cover what the agent will/won't do, what
  gets stored on your machine, and where responsibility sits when the agent takes an
  action on your behalf.
- The confirmation gate will stop and ask before any risky action (sending a
  message, deleting something, etc.) — read what you're approving rather than
  clicking through on habit. See `TERMS.md`'s "confirmation gate" section for why
  this matters more than it might seem.

## When something goes wrong

Run this after hitting a bug, a crash, or anything that surprised you — it builds a
shareable report from the task's own trace log, without needing you to remember or
retype exactly what happened:

```
python -m src.observability.beta_report logs/ --notes "describe what happened, in your own words"
```

This uses the most recent task in your `logs/` directory. If you know exactly which
task, you can point it at that file directly instead:

```
python -m src.observability.beta_report logs/task_20260816T120000_ab12cd.jsonl --notes "..."
```

This writes a Markdown report to `beta_reports/` (in your current directory) — open
it, skim it once, and share it however's easiest (paste into an issue, attach to an
email, send in whatever channel we've set up for this).

**Screenshots are not included by default.** If the report alone doesn't explain
what happened and you're comfortable sharing a screenshot from that specific task,
re-run the same command with `--include-screenshots` added — it'll copy over only
that task's own screenshots (never your whole history) and print a reminder to
glance at them before sharing, since a screenshot can show more of your screen than
just the bug.

## What's genuinely useful to report

- Anything the agent got wrong, even if it seemed minor or you just clicked past it.
- Any moment the confirmation gate felt confusing, or didn't show up when you
  expected it to.
- Anything that felt slow, that crashed, or that needed a restart.
- If a task looked like it succeeded but the actual result was wrong.

You don't need to diagnose the bug yourself — the trace excerpt in the generated
report does most of that work. A one-line description of what you were trying to do
and what happened instead is enough.

## What happens after you report something

Findings get triaged into `docs/BETA_FINDINGS.md` (not visible to testers by
default, but ask if you want to see how something you reported was handled) — each
one gets a real disposition (fixed, a known accepted limitation, or not a real
issue), not just silently filed away.

## Questions

If anything in this guide is unclear, or something about how the agent behaves
doesn't match what `TERMS.md`/`PRIVACY.md` describe, that's itself worth reporting —
those documents are meant to be accurate, and a beta tester finding a gap between
"documented" and "actual" behavior is exactly the kind of thing this phase exists to
catch.
