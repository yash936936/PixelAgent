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

### [2026-08-17] Pre-flagged risk: OCR now uses `--psm 6` (single uniform text block), unvalidated on
  complex multi-panel real desktop screenshots
- **Status: ACCEPTED (pre-flagged ahead of beta, not discovered by a tester)**
- **What:** `src/perception/ocr.py`'s Tesseract config was changed to `--psm 6` (forces Tesseract to treat
  the entire screenshot as one uniform text block) to fix a real failure where a newer Tesseract build
  (5.5.0.20241111) could not find text inside a solid-color button at all, even with the project's existing
  `textord_min_linesize=1.0` mitigation. Full detail in `docs/DECISIONS.md`'s 2026-08-17 entry.
- **The real, unvalidated risk:** `read()` runs against the full desktop screenshot in production
  (`src/action/action_router.py`), not a cropped region. `--psm 6` skips Tesseract's normal multi-column/
  multi-region layout analysis, which was only tested against this project's own simple, 1-2-line test
  fixtures. On a genuinely complex real screen (multiple windows, a taskbar, several distinct widget
  regions), this could plausibly produce worse text ordering or merged/garbled results compared to the
  prior default (PSM 3) -- this project has no test coverage either way, and the sandboxed dev environment
  this fix was made in cannot render or test against real, complex desktop screenshots.
- **If you hit this during beta:** anything where OCR-based `target_text` clicks seem to target the wrong
  element, miss an element that's clearly visible, or behave inconsistently on a busy/cluttered screen is
  worth reporting via `beta_report.py` even if it doesn't look OCR-related at first glance -- this is
  exactly the failure mode this finding is watching for.
- **Disposition:** accepted for now -- the prior config failed completely and unconditionally for an
  ordinary button, which is a worse starting point than an unvalidated risk on more complex screens.
  Revisit if real beta usage surfaces a genuine regression.

*(No tester-reported findings yet -- the entry above was added proactively by the engineering side ahead
of the beta window opening, not from a real report. See `docs/DECISIONS.md`'s 2026-08-16 entry for when
this file's structure and `beta_report.py` were built and tested.)*
