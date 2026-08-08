# Replacement for docs/PHASES.md's Phase 11 section only

Everything else in your real PHASES.md (Phases 0-10, 12-18, the deployment readiness
gate, and the deferred-features list) is unchanged — only the Phase 11 block needs
updating. Find the section starting with "## Phase 11 — Packaging & distribution" in
your real file and replace it with the block below.

---

## Phase 11 — Packaging & distribution
**Status: COMPLETE (2026-08-02) in code; installer FULLY VERIFIED end-to-end on real
Windows hardware (2026-08-08).** Also a major, unplanned capability unlock: PySide6
turned out to actually install and run in this project's Linux build environment
(`pip install PySide6==6.11.1`), which was not known to be possible before this phase.
Every GUI test now runs and passes here — the full 395-test suite (347 non-GUI + 48 GUI)
ran together in one pass for the first time in this project's history.

**2026-08-08 update:** the user completed the first full real-hardware build → install →
run → uninstall cycle for `installer/pixel-agent.iss`, closing the "cannot compile or
test in this Linux build environment" caveat that applied to the installer since it was
first written. Five real bugs were found and fixed in the process (wrong `README.md`
source path, `OutputDir` resolving one directory too high, a PyInstaller `--name`
mismatch against `MyAppExeName` that produced a build which compiled clean but had a
broken Start Menu shortcut, PyInstaller's bundled Playwright having no Chromium binary of
its own, and — found in the same live-run session but NOT a packaging bug — a dead
`gemini-2.5-flash` default in `config.py`). Full detail in `docs/DECISIONS.md`'s
2026-08-08 entry and `docs/RELEASE.md`'s "Known issues found on first real build"
section.

| File | Description |
|---|---|
| `pyproject.toml` (new) | Proper packaging metadata. **Actually built and verified**: `python -m build --wheel`, installed, confirmed `pixel`/`pixel-gui` console commands genuinely work — not just written and assumed correct. |
| `src/main.py` (updated) | New `cli_main()`, a zero-argument wrapper around `main(instruction)` for the `pixel` console entry point (`console_scripts` are invoked with no args). |
| `src/gui/app.py`, `src/gui/setup_wizard_logic.py` (new), `src/gui/widgets/setup_wizard.py` (new) | First-run setup wizard — closes a real gap where `config.load()` ran before `QApplication` even existed. Logic kept Qt-free and fully unit-tested; the `QDialog` itself constructed and exercised offscreen with real PySide6. **Confirmed working on a genuinely clean install, 2026-08-08** — an earlier apparent skip of the wizard was traced to a leftover `.env` from prior testing, not a real bug. **Known gap found 2026-08-08:** the wizard has no field for `LLM_MODEL`, so every install silently inherits `config.py`'s hardcoded default with no in-wizard override — worth a future addition given the default was found to be a dead model on the same date. |
| `installer/pixel-agent.iss` (new, updated 2026-08-06 and 2026-08-08) | Complete Inno Setup script — per-user install, optional Tesseract/Chromium components, pre-seeds `TESSERACT_CMD`. **2026-08-06:** fixed `SourceDir`/`OutputDir` path resolution and documented the `robocopy`-over-`Copy-Item` staging fix. **2026-08-08:** fixed the PyInstaller `--name`/`MyAppExeName` mismatch (build-side, not a script change) and added a `PLAYWRIGHT_BROWSERS_PATH` line to the `.env`-seeding `[Code]` section, fixing a crash on the first browser-target-type task caused by PyInstaller's bundled Playwright having no Chromium of its own. **Now built, compiled, installed, and run successfully on real Windows hardware — no longer "written but unverified."** |
| `docs/RELEASE.md` (new, updated 2026-08-06 and 2026-08-08) | The real build/sign/release process. **As of 2026-08-08, the verified/unverified table shows PyInstaller bundling, the Inno Setup compile, install/SetupWizard/uninstall, and a real completed browser-target-type task from the installed build as all `[VERIFIED]`** — genuinely run, not assumed. Code signing remains the one deliberately-unset-up step (no certificate exists). A desktop-target-type task has not yet been confirmed from the installed build specifically (only from source, via Phase 7). |

**Phase 11 success criterion (MET for the software side; installer half now also MET as
of 2026-08-08):** someone who isn't the author can download one file, install it, and get
to a working first task with no terminal/source access. The `SetupWizard` closes the
"no terminal access" gap. **The "download one file" half of this criterion — the
installer actually compiling and running correctly on a real Windows machine — has now
been done and confirmed, closing what was previously the single largest open item in
this phase.** What remains open within Phase 11 specifically: the `LLM_MODEL` default
gap (a real, currently-live bug affecting every fresh install until fixed at the source
in `config.py`), and confirming a desktop-target-type task specifically from the
installed build rather than only from source.
