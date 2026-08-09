# RELEASE_ENGINEERING.md — Phase 14 status and known gaps

**Status: written, NOT run.** No GitHub Actions runner is available in this build
environment to actually trigger either workflow — both are written correctly per
GitHub Actions' documented YAML syntax and this project's own real commands (pulled
directly from `docs/RELEASE.md` and `docs/DOCKER.md`, not guessed), but neither has
executed even once.

## What exists

- **`.github/workflows/test.yml`** — runs on every push/PR: the non-GUI suite, the
  integration suite (with real Tesseract + Chromium installed on the runner), the GUI
  suite (offscreen Qt via `xvfb-run`), and both eval harnesses (adversarial boundary,
  injection signal) as a regression check.
- **`.github/workflows/release.yml`** — runs on a version tag push: builds the Windows
  installer on a `windows-latest` runner (automating the exact manual sequence from
  `docs/RELEASE.md`, including the `--name pixel-gui` fix from the 2026-08-08
  bug-fix session), builds and smoke-tests the browser-only Docker image, and creates
  a **draft** GitHub release (not auto-published) with both artifacts attached.
- **`CHANGELOG.md`** — user-facing release notes, separate from `docs/DECISIONS.md`'s
  developer-facing technical log, per `docs/PHASES.md`'s Phase 14 file table.

## What's genuinely uncertain and should be checked on first real run

1. **Inno Setup on `windows-latest`.** GitHub's hosted runners are documented to
   include a set of pre-installed tools that changes over time. Whether `ISCC.exe` at
   the exact path `docs/RELEASE.md` assumes (`C:\Program Files (x86)\Inno Setup 6\`)
   is actually present on the runner has not been checked against GitHub's current
   tool manifest. If it's missing, the workflow needs an explicit Inno Setup install
   step added before the compile step.
2. **Tesseract/Chromium staging is deliberately NOT automated in `release.yml`.**
   `docs/RELEASE.md` flags both as separately-licensed third-party binaries needing a
   real license check before redistribution — automating that download inside CI
   without a human explicitly acknowledging the license each time felt like the wrong
   default to silently build in. The release workflow as written produces an
   installer with Tesseract/Chromium components *available* but not staged with
   actual binaries unless a human adds that step deliberately. Worth a real decision,
   not a default.
3. **`GEMINI_API_KEY_CI_SMOKETEST` secret does not exist yet.** The Docker
   smoke-test step in `release.yml` references a GitHub Actions secret that needs to
   be created in the repo's settings before this workflow can run successfully — using
   a real, dedicated (ideally low-quota or free-tier, separate from your personal
   development key) API key for CI smoke tests, not your personal one. Given
   tonight's git-history secret leak, treat this with real care: create it via
   GitHub's secrets UI, never commit it anywhere, and consider a key with usage limits
   tight enough that a CI misconfiguration can't run up real cost or get rate-limited
   in a way that blocks releases.
4. **The eval regression check's exact output-parsing regex is unverified**
   (see `check_eval_regression.py`'s own docstring) — confirm
   `eval/adversarial_boundary_eval.py`'s actual print format matches what the script
   expects before trusting this gate; adjust if not.

## Known gap: no automated rollback

`docs/PHASES.md`'s Phase 14 success criterion states: "a bad release can be rolled
back without manual intervention." **This is not implemented.** `release.yml`'s final
job only prints a reminder of the manual rollback steps (delete the bad release/tag,
re-tag a known-good commit). Building genuine automated rollback — for instance,
auto-reverting a `latest` alias/pointer, or gating promotion from draft to published
behind a health check — is a real design decision on par with Phase 8's encryption
key-management choice, and deserves the same "decide deliberately, document the
reasoning" treatment rather than being bolted on here. Recorded honestly as unmet
rather than glossed over, matching this project's established convention (see Phase
10's own honest zero-result entry in `docs/DECISIONS.md` for the precedent).

## Phase 14 success criterion, honestly assessed

> "A merge to main automatically produces a tested, installable build (native + both
> Docker variants); a bad release can be rolled back without manual intervention."

- **Tested build on every merge:** the mechanism exists (`test.yml`) but has never
  actually run — first real push/PR to this repo after adding it is the real test.
- **Automatically produces an installable build:** `release.yml` exists and covers
  the native Windows installer and the browser-only Docker image. It does NOT cover
  Phase 13's Windows-VM Docker variant, since that phase is currently on hold (see
  `docs/DECISIONS.md`'s 2026-08-09 entry) — "both Docker variants" in the criterion
  above is not yet fully met and can't be until Phase 13 resumes.
- **Rollback without manual intervention:** NOT met, per the section above.

This phase should be considered **partially complete** until at least one real tag
push has been run through `release.yml` successfully and the rollback gap has either
been closed or explicitly accepted with reasoning recorded, per this project's own
`docs/DECISIONS.md` convention for open items.
