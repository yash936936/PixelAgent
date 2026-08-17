# Beta Findings

**Purpose:** the append-only log of everything found during Phase 18's real-user field
testing (5-10 beta users, ~two weeks, per `docs/PHASES.md`'s Phase 18 spec). This is
`docs/DECISIONS.md`'s counterpart for *findings from real usage* rather than
*engineering decisions* — a beta tester's report goes here first, gets triaged, and
only produces a `docs/DECISIONS.md` entry once someone actually acts on it (fixes it,
defers it, or explicitly accepts it as a known limitation).

**How a finding gets here:** a beta tester runs
`python -m src.observability.beta_report <log_dir_or_file> --notes "..."` after
hitting something worth reporting (see `docs/BETA_GUIDE.md` for the tester-facing
instructions) and shares the generated Markdown report however they'd normally report
a bug. Each finding below should link back to (or paste the relevant excerpt of) that
report, not just describe the bug from memory — the whole point of the audit-trail
export (Phase 17) is to keep "what actually happened" and "what someone remembers
happening" from silently diverging.

**Status values, matching `docs/PHASES.md`'s general convention elsewhere:**
- `NEW` — reported, not yet triaged.
- `TRIAGED` — looked at, next step decided (see "Disposition").
- `FIXED` — a real code/doc change landed; linked `docs/DECISIONS.md` entry.
- `ACCEPTED` — a real, known limitation, not being fixed right now, with reasoning
  recorded (same "accepted, not silently dropped" convention as Phase 16's Findings
  2-5).
- `WONT_FIX` — investigated and determined not to be a real issue, or out of scope.

---

## Template for a new entry

Copy this block for each new finding. Keep entries in chronological order (oldest
first), same convention as `docs/DECISIONS.md`.

```
### [YYYY-MM-DD] Short title of what was reported
- **Reported by:** (tester's name/handle, or "anonymous" if preferred)
- **Status:** NEW
- **Pixel version / OS:** (from the beta report's Environment section)
- **What happened:** (in the tester's own words, or a direct excerpt from their
  --notes)
- **Trace excerpt:** (paste the relevant Actions lines from their beta report, or
  attach/link the full report — never paste raw, unreviewed screenshot content
  here; see "Handling screenshots" below)
- **Disposition:** (filled in once triaged — fix now / accept / won't-fix, with
  reasoning)
- **Linked `docs/DECISIONS.md` entry:** (once FIXED)
```

---

## Handling screenshots

Beta reports do **not** include screenshots by default (`beta_report.py`'s own
design, see `PRIVACY.md`). If a tester opts in and shares one, treat it the same way
`PRIVACY.md` already asks the project to treat any screenshot: review it before
pasting it into this file or any shared/public location, since it can show more than
the specific bug it was meant to illustrate. Prefer describing what the screenshot
shows over embedding it directly in this file, unless it's already been reviewed for
anything beyond the reported issue.

---

## Findings

*(No findings recorded yet — this section will be populated once Phase 18's real
beta cohort starts reporting. This file's structure and the `beta_report.py` tool
that feeds it were built and tested 2026-08-16, per `docs/DECISIONS.md`'s matching
entry, ahead of that beta window actually opening.)*
