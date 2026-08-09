# Phase 14 — what's in this zip

Phase 13 was not merged into your repo (it was only ever a standalone review package
from the last exchange), so there's nothing to literally "revert" on your machine —
just don't apply that earlier zip. This package instead marks Phase 13 on-hold in your
docs and adds Phase 14's real files.

## Files

1. **`.github/workflows/test.yml`** — new. Runs non-GUI, integration, and GUI test
   suites plus both eval harnesses on every push/PR.
2. **`.github/workflows/release.yml`** — new. Builds the Windows installer + Docker
   image on a version-tag push, publishes a **draft** GitHub release.
3. **`.github/workflows/scripts/check_eval_regression.py`** — new. Small helper the
   test workflow uses to catch an eval-score regression; its output-parsing regex is
   flagged unverified in its own docstring — check against the real eval script's
   print format before trusting it blindly.
4. **`CHANGELOG.md`** — new. User-facing release notes, separate from `DECISIONS.md`.
5. **`docs/RELEASE_ENGINEERING.md`** — new. Honest status of Phase 14: what's genuinely
   uncertain (Inno Setup on the GitHub runner, un-automated Tesseract/Chromium staging,
   a secret that doesn't exist yet), and the one success-criterion sub-item
   (automated rollback) that's explicitly NOT met.
6. **`docs/PHASES_Phase13_onhold_block.md`** — **not a drop-in file.** Replace Phase
   13's status line in your real `docs/PHASES.md` with this block. Plan/file table
   underneath stays as-is — only the status changed.
7. **`docs/DECISIONS_new_entry_phase14.md`** — append to the END of your real
   `docs/DECISIONS.md` (chronological, oldest-first, same convention as last time).

## Before this actually does anything

Two setup steps needed on GitHub's side, not just files in your repo:

1. **Create a `GEMINI_API_KEY_CI_SMOKETEST` secret** in your repo's Settings → Secrets
   and variables → Actions. Use a dedicated key, not your personal one — ideally one
   with tight usage limits, given tonight's earlier git-history key leak. Don't reuse
   whatever key you rotate to for your own local development.
2. **Confirm Inno Setup is actually present on `windows-latest`** the first time
   `release.yml` runs — `docs/RELEASE_ENGINEERING.md` flags this as unverified. If the
   compile step fails looking for `ISCC.exe`, that's why; the workflow needs an
   explicit install step added.

## Suggested next step

Apply the files, push to `main`, and watch `test.yml` actually run for the first time
— that's the real verification this workflow needs, the same way `docs/RELEASE.md`
only became trustworthy once someone actually ran it end-to-end on 2026-08-08.
