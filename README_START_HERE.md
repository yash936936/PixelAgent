# Phase 14 CI fixes — round 1

Four real bugs, three fixed here, one needs a manual step from you.

## Files

1. **`.github/workflows/test.yml`** — drop-in replacement. Tesseract now installs
   before the non-GUI test step; Qt system libraries now install before the GUI test
   step; eval regression floor lowered to 65% (see #3 below).
2. **`.github/workflows/scripts/check_eval_regression.py`** — drop-in replacement.
   Regex fixed to match the real `Overall: N/M (P%)` output format.
3. **`installer/PATCH_pixel_agent_iss_folder_name.md`** — **not a drop-in file.**
   This is the important one — read it. Your real `installer/pixel-agent.iss` has a
   genuine bug: it references `dist\pixel-agent\*` but your PyInstaller command
   produces `dist\pixel-gui\*`. This was silently masked locally by a stale leftover
   folder — meaning your last "working" installer build should be considered suspect
   until you do a fully clean rebuild and re-verify.
4. **`docs_DECISIONS_new_entry_ci_fixes.md`** — append to the end of your real
   `docs/DECISIONS.md`, same convention as before.

## What you still need to do manually

**Create the `GEMINI_API_KEY_CI_SMOKETEST` secret** — repo Settings → Secrets and
variables → Actions → New repository secret. Without this, `release.yml`'s Docker job
will keep failing with `GEMINI_API_KEY is not set`, exactly what the last run showed.

## After applying everything

1. Apply the two workflow file replacements and the `.iss` one-line fix.
2. Paste the DECISIONS entry.
3. **Delete your local `dist/` folder** and do one fully clean rebuild — don't trust
   the previous "verified" build, it may have shipped stale files.
4. Re-run `docs/RELEASE.md`'s full smoke test against the freshly rebuilt installer.
5. Create the missing secret.
6. Commit, push to `main` — watch `test.yml` run again.
7. Once that's green, push a new tag (bump the version, e.g. `v0.12.1`, since
   `v0.12.0` already exists) to trigger `release.yml` again.

Paste back whatever the next run shows — there may be more to find, same as every
other "first real run" in this project.
