### [2026-08-11] Phase 14 — first fully green release run; two more real bugs found
  and fixed (dead model default, missing release-write permission)
- **Type:** Overwrite (multiple)
- **File(s) affected:** `src/config.py`, `.env.example`, `.env`, `tests/brain/test_planner.py`,
  `tests/test_main.py`, `.github/workflows/release.yml`.
- **What changed:** Continuing directly from the 2026-08-11 CI-fixes entry, two more real
  issues surfaced and were fixed on the way to a fully working release pipeline:
  1. **`gemini-2.5-flash`'s dead-model 404 was still live at the source**, not just
     worked around on one machine as of the 2026-08-08 entry. `config.py`'s
     `llm_model` default, `.env.example`, and the local `.env` all still referenced it;
     `tests/brain/test_planner.py` (10 occurrences) and `tests/test_main.py` (1) also
     hardcoded it as a test parameter/mock default. All replaced with
     `gemini-3.5-flash-lite` (confirmed GA via a live web search against Google's own
     API changelog before committing to the name, not assumed). One transcription slip
     during the fix (a regex intended to also catch `gemini-3.5-flash` as a bare string
     accidentally matched inside `gemini-3.5-flash-lite` too, due to `\b` only checking
     a boundary before the match rather than requiring no suffix at all, producing
     `gemini-3.5-flash-lite-lite` in `.env`) was caught by a follow-up `grep` before
     committing, not left in.
  2. **`release.yml`'s `create-release` job failed with 403 "Resource not accessible by
     integration."** Root cause: GitHub Actions' default `GITHUB_TOKEN` only has
     read-level repo access unless a workflow explicitly requests more; `release.yml`
     never declared `permissions: contents: write` for the job that calls
     `softprops/action-gh-release`. Fixed by adding that block to the `create-release`
     job specifically (job-scoped, not workflow-wide, so no other job gets broader
     permissions than it needs).
  3. **A tagging process note, not a code bug**: `v0.12.2` and `v0.12.3` were both cut
     before their respective fixes had actually been verified reachable in a real CI
     run (v0.12.2 was tagged from the same commit as the model fix, correctly, but
     v0.12.3's run failed on the permissions issue above, which wasn't yet fixed when
     that tag was cut). `v0.12.4`, tagged after the permissions fix, is the first tag
     to produce a fully green run across all four `release.yml` jobs. Earlier tags left
     in place as history; no tags were force-moved.
- **Why:** Direct continuation of closing out Phase 14's verification gap — the same
  "written vs. actually run" discipline this project has followed since Phase 7.
- **Impacts:** **`v0.12.4`'s release run is the first fully green run in this project's
  history** — Build Windows installer, Build Docker images (browser-only, including a
  real Gemini API smoke-test call), Create GitHub release (draft), and the rollback
  reminder job all succeeded. This closes `docs/RELEASE_ENGINEERING.md`'s three
  previously-flagged uncertainties for the installer/Docker halves (Inno Setup was
  confirmed present on `windows-latest`; the `GEMINI_API_KEY_CI_SMOKETEST` secret works
  correctly end-to-end). **Still open, unchanged by this pass**: automated rollback
  remains unimplemented (the reminder job only prints manual steps); Phase 13's
  Windows-VM Docker variant is still on hold, so "both Docker variants" in Phase 14's
  original success criterion is met only for the browser-only variant. `docs/PHASES.md`'s
  Phase 14 should be marked **COMPLETE** for everything within its actually-achievable
  scope (native installer + browser-only Docker + automated testing), with rollback and
  the Windows-VM Docker variant explicitly carried forward as known, accepted gaps
  rather than silently dropped.
