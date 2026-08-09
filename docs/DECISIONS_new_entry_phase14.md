### [2026-08-09] Phase 13 put on hold; Phase 14 (CI/CD & release engineering) written
- **Type:** New (multiple) + Scope/priority change (no code reverted — see note below)
- **File(s) affected:** `.github/workflows/test.yml` (new), `.github/workflows/release.yml`
  (new), `.github/workflows/scripts/check_eval_regression.py` (new), `CHANGELOG.md` (new),
  `docs/RELEASE_ENGINEERING.md` (new), `docs/PHASES.md` (Phase 13 status updated to ON
  HOLD; Phase 14 file table implemented).
- **What changed:**
  1. **Phase 13 (Windows-in-Docker desktop automation) put on hold.** A first pass at
     this phase's files was written 2026-08-09 (Dockerfile, provision.ps1,
     docker-compose.desktop.yml, reset-snapshot.sh, docs/DOCKER_DESKTOP.md) but was never
     merged into the working repo — delivered as a standalone package for review only.
     Decision made same-day to not proceed with merging those files yet: this is the first
     phase in the project's history requiring infrastructure (a Linux host with `/dev/kvm`
     exposed) genuinely different from anything used in Phases 7-12's live-run
     verification, which all ran on the same real Windows machine. Rather than build out
     and attempt to verify a phase against hardware not confirmed available, deferred it
     in favor of phases that can actually be exercised now. The written files are not
     discarded — available to merge whenever this phase resumes.
  2. **Phase 14 (CI/CD & release engineering) implemented.** `test.yml` runs the non-GUI,
     integration, and GUI test suites plus both eval harnesses on every push/PR — the
     first automated test run in this project's history (every one of the 395+ tests
     referenced throughout `docs/STATUS.md` has, until now, been run manually).
     `release.yml` automates the Windows installer build (including the `--name
     pixel-gui` fix from the 2026-08-08 live debugging session, so that exact mistake
     can't silently recur in an automated release) and the browser-only Docker image
     build+smoke-test, publishing both as a **draft** (not auto-published) GitHub
     release. `CHANGELOG.md` added as the user-facing counterpart to this file's
     developer-facing log.
  3. **Deliberately left open, not glossed over:** `docs/PHASES.md`'s Phase 14 success
     criterion includes automated rollback ("a bad release can be rolled back without
     manual intervention") — NOT implemented. `release.yml`'s final job only prints
     manual rollback steps. This is recorded as a genuine gap, same honesty convention
     as Phase 10's zero-result entry, rather than claiming the criterion is met when
     it isn't. See `docs/RELEASE_ENGINEERING.md` for full detail on this and three other
     unverified assumptions (Inno Setup's presence on `windows-latest`, deliberately
     un-automated Tesseract/Chromium staging in CI due to licensing, and a not-yet-created
     `GEMINI_API_KEY_CI_SMOKETEST` secret).
- **Why:** Direct response to explicit direction: skip Phase 13 for now (infrastructure
  not confirmed available), mark it on hold rather than abandoned, and move to Phase 14,
  which — unlike Phase 13 — automates work already proven to matter this session (the
  entire 2026-08-06/08-08 installer debugging cycle was done by hand, repeatedly, exactly
  what `test.yml`/`release.yml` exist to prevent going forward).
- **Impacts:** `docs/PHASES.md`'s Phase 13 section status changed to ON HOLD (plan and
  file table unchanged, just deprioritized) — Phase 14 section should be marked
  IN PROGRESS / PARTIALLY COMPLETE, not COMPLETE, per `docs/RELEASE_ENGINEERING.md`'s
  own honest assessment (test workflow untested against a real run; release workflow has
  3 unverified assumptions and 1 explicitly unmet sub-criterion). Next real action:
  push this to trigger `test.yml` for the first time and see what actually happens
  against real GitHub infrastructure, rather than assuming the written YAML is correct.
