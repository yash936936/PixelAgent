# Changelog

All notable user-facing changes to PixelAgent are documented here. This is separate
from `docs/DECISIONS.md`, which is the developer-facing, append-only technical log —
this file is for people deciding whether/how to update, not for the full reasoning
behind each change.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/); versioning
follows [Semantic Versioning](https://semver.org/), per `docs/RELEASE.md`'s own
versioning section.

## [Unreleased]

### Fixed
- Windows installer: fixed a packaging bug where the bundled Playwright runtime had
  no Chromium binary of its own, causing the first browser-target-type task after a
  fresh install to crash. The installer now points the app at its own staged
  Chromium copy automatically.
- Windows installer: fixed several build-script path-resolution bugs
  (`SourceDir`/`OutputDir`, a missing `README.md` reference, an executable-name
  mismatch) that could produce an installer that compiled successfully but failed to
  launch correctly.

### Known issues
- The default Gemini model (`gemini-2.5-flash`) is deprecated by Google for new API
  callers and currently returns an error on first use. Until this is fixed at the
  source, set `LLM_MODEL=gemini-3.5-flash-lite` manually in your `.env` file after
  installing.

## [0.11.0] — 2026-08-02

### Added
- Docker deployment (browser-only mode) — see `docs/DOCKER.md`.
- Windows installer (`PixelAgent-Setup-<version>.exe`) via Inno Setup, with a
  first-run setup wizard for entering your Gemini API key and Chrome profile.
- `pixel`/`pixel-gui` console commands via proper Python packaging.

### Changed
- Packaging moved to `pyproject.toml`-based builds.

## [0.10.0] and earlier

Pre-dates this changelog. See `docs/DECISIONS.md` for the full development history
from initial architecture through Phase 10 (memory, self-improvement loop, semantic
risk layer, encryption-at-rest, injection-signal detection).
