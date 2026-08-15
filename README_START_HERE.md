# Phase 16 — security review, first pass

## Files

1. **`docs/SECURITY_REVIEW.md`** — new, drop-in. The actual review: 7 findings,
   a summary table, and priority-ordered recommendations. Read this one directly
   — it's the real deliverable.
2. **`eval/adversarial_cases_ADDITIONS.jsonl.md`** — **not a drop-in file.** 12
   new adversarial cases, written specifically adjacent to the 11 real failures
   your own CI run surfaced tonight (`adv_005`, `adv_015`, `adv_018`, etc.) rather
   than generic filler. Before merging: confirm the real file's exact schema
   (field names) and current highest `adv_NNN` ID, then append and renumber as
   needed — the note at the top of the file spells this out.
3. **`docs/DECISIONS_new_entry_phase16.md`** — append to the end of your real
   `docs/DECISIONS.md`.

## The one finding worth acting on first

Finding #1 in the review: add a local pre-commit secret-scanning hook (e.g.
`gitleaks` or `detect-secrets`). This isn't hypothetical — it's a direct response
to the real key leak from earlier tonight. GitHub's push protection caught that
one, but that's a server-side safety net you got lucky to have, not something
this project's own workflow guarantees for every future commit or every other
git host.

## What Phase 16 needs to actually be "done"

Per its own success criterion, findings need to be **triaged** — for each of the
7 findings, decide "fix now," "fix later (and schedule it)," or "explicitly
accept the risk," and record that decision in `docs/DECISIONS.md`. This review
provides the findings and a recommended priority order; the actual triage
decisions are yours to make, not something I can decide on your behalf.
