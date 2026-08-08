# RELEASE.md — Build, sign, and release PixelAgent (Phase 11)

This is the real build process for producing an installable Windows distribution, per
`docs/PHASES.md`'s Phase 11. **Every step below must be run on a real Windows machine** —
this project's Linux build/test environment can verify the Python packaging
(`pyproject.toml`, the `pixel`/`pixel-gui` console entry points) but cannot build, run, or
sign a Windows installer. Steps marked **[VERIFIED]** were actually run and confirmed
working on a real Windows machine; steps marked **[UNVERIFIED]** are written correctly
per each tool's documented usage but have not been executed.

## 1. Prerequisites (Windows machine)

- Python 3.11+ with this repo's dependencies installed: `pip install .[gui,windows]`
- [PyInstaller](https://pyinstaller.org/) — `pip install pyinstaller`
- [Inno Setup](https://jrsoftware.org/isinfo.php) (free) — provides `ISCC.exe`, the
  installer compiler `installer/pixel-agent.iss` targets
- A real Gemini API key for a final smoke test of the built installer (see step 5)

## 2. Building the Python app **[VERIFIED — 2026-08-08]**

PyInstaller bundles a real Python runtime plus every dependency into a standalone
`dist/pixel-agent/` directory — this is what `installer/pixel-agent.iss`'s `[Files]`
section packages, not the raw source checkout.

The executable name matters and must match `pyproject.toml`'s `pixel-gui` console entry
point (`pixel-gui = "src.gui.app:main"`), which is also what `pixel-agent.iss`'s
`MyAppExeName` and every `[Icons]`/`[Run]` line reference. Using a mismatched `--name`
(e.g. `pixel-agent`) produces a working `.exe` that the installer's shortcuts can't find —
confirmed live, see the "Known issues found on first real build" section at the bottom.

```powershell
pyinstaller --name pixel-gui --windowed --onedir --noconfirm `
    --add-data "docs/design-tokens;docs/design-tokens" `
    src/gui/app.py
```

`--add-data` is required: `src/gui/style.py` reads `docs/design-tokens/tokens.json` at
runtime, and PyInstaller does not bundle non-Python files automatically. Verify
`dist/pixel-gui/pixel-gui.exe` actually launches before proceeding — a broken
PyInstaller bundle will still let Inno Setup build a technically-valid but non-functional
installer, since Inno Setup has no way to know the app inside is broken.

**Known gap, not fixed by this step alone:** PyInstaller's bundled copy of Playwright
does NOT include a Chromium binary — Playwright always expects one at a separate,
OS-level cache path. See step 3 and the `[Code]` section note in `pixel-agent.iss` for
how this build now handles it.

## 3. Staging Tesseract and Chromium **[PARTIALLY VERIFIED — 2026-08-08]**

`installer/pixel-agent.iss`'s optional `tesseract`/`chromium` components expect these
directories to exist before compiling:

```
installer/staging/tesseract/   ← copy of a real Tesseract install (e.g. from
                                  https://github.com/UB-Mannheim/tesseract/wiki)
installer/staging/chromium/    ← Playwright's Chromium build, found after running
                                  `playwright install chromium` at:
                                  %LOCALAPPDATA%\ms-playwright\chromium-<version>\chrome-win
```

Both are real, separately-licensed third-party binaries — check their respective licenses
before redistributing them inside this installer. If skipping either (smaller installer,
person installs Tesseract/uses their own Chrome separately), remove the corresponding
`[Components]`/`[Files]` lines in `pixel-agent.iss` rather than leaving a component that
silently does nothing (`skipifsourcedoesntexist` means the installer will build fine, but
selecting an empty component installs nothing, which reads as a bug to whoever runs it).

**Use `robocopy`, not `Copy-Item -Recurse` with a wildcard source.** Confirmed live
(2026-08-06): `Copy-Item "source\*" -Destination dest -Recurse` fails partway through a
nested directory tree with `Container cannot be copied onto existing leaf item` — a known
PowerShell quirk with this exact pattern, not specific to this project.

```powershell
robocopy "C:\Program Files\Tesseract-OCR" installer\staging\tesseract /E
robocopy "$env:LOCALAPPDATA\ms-playwright\chromium-<version>\chrome-win" installer\staging\chromium /E
```

`robocopy`'s exit codes are not the usual 0-success convention — 0 through 7 all mean
success; only 8+ indicates a real error.

**Critical: staging Chromium alone is not sufficient.** Copying files into
`installer/staging/chromium/` only gets them onto the end user's disk at
`{app}\chromium\` — it does not tell the bundled Playwright runtime to look there instead
of its normal (empty, in this build) cache path. Confirmed live (2026-08-08): a fully
successful build and install still crashed on the first browser-target-type task with
`Executable doesn't exist at ...\.local-browsers\chromium-<version>\chrome-win\
chrome.exe`. Fixed by having `pixel-agent.iss`'s `[Code]` section write
`PLAYWRIGHT_BROWSERS_PATH={app}\chromium` into the generated `.env` whenever the
`chromium` component is selected — the app already loads `.env` into its process
environment at startup, and Playwright itself reads `PLAYWRIGHT_BROWSERS_PATH` from the
OS environment at launch time, so no PyInstaller or `config.py` change is required. This
is now built into `pixel-agent.iss` directly; nothing extra to do here beyond staging the
files correctly.

## 4. Building the installer **[VERIFIED — 2026-08-08, after two fixes]**

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\pixel-agent.iss
```

Output: `dist/installer/PixelAgent-Setup-<version>.exe`. Confirm the version in that
filename matches `pyproject.toml`'s `[project].version` — these are not automatically
kept in sync; bump both by hand for every release until Phase 12's CI/CD automates it.

**Two real bugs were found and fixed getting this step to compile** — see "Known issues
found on first real build" below for full detail. Both fixes are already applied in the
current `pixel-agent.iss`; nothing further to do here on a fresh checkout of this file.

## 5. Manual smoke test **[VERIFIED — 2026-08-08]**

Before calling any build a release, actually run the installer on a clean-ish machine (or
at minimum a machine without a pre-existing `.env` for this app) and confirm, per Phase 11's
own success criterion:

1. The installer runs without requiring admin rights (`PrivilegesRequired=lowest`). **✓**
2. `pixel-gui.exe` launches and shows `SetupWizard` (`src/gui/widgets/setup_wizard.py`) —
   not a raw error — since no `.env` exists yet. **✓ confirmed on a genuinely clean
   install** (an earlier attempt against a leftover `.env` from prior testing skipped
   straight to the Dashboard — not a bug, just not a true first-run test; re-confirmed
   clean after a full uninstall).
3. Entering a real Gemini API key and completing the wizard reaches the main window. **✓**
4. `python -m src.doctor` (installed via `pip install .[windows]` and run from the
   installed app's own Python environment, if bundled, or a separate check if not) reports
   Tesseract/Chromium as found, if those components were selected during install.
5. Uninstalling via "Uninstall PixelAgent" in the Start Menu actually removes the app
   directory. **✓ confirmed**.
6. A real browser-target-type task completes end-to-end (`status: done`) — the actual
   proof the Chromium-path fix works, not just that the installer compiles. **✓ confirmed**
   (`"open https://chat.qwen.ai/"` completed in 2 steps, 0 errors).

## 6. Code signing **[NOT YET SET UP — no certificate exists]**

An unsigned `.exe` triggers Windows SmartScreen's "Unknown publisher" warning on first
run, which meaningfully hurts trust for anyone downloading this from outside a direct,
known-source link. Setting this up requires:

1. Purchasing a code-signing certificate from a recognized CA (e.g. DigiCert, Sectigo) —
   this has a real ongoing cost and an identity-verification process; not something this
   pass can set up without the actual business/individual details of the signer.
2. Uncommenting and configuring `pixel-agent.iss`'s `SignTool=`/`SignedUninstaller=yes`
   directives once a certificate exists, per
   [Inno Setup's signing documentation](https://jrsoftware.org/ishelp/index.php?topic=setup_signtool).

Until this is set up, distribute the unsigned installer with a clear note that
SmartScreen's warning is expected and how to bypass it ("More info" → "Run anyway") for
anyone testing a pre-signed build.

## 7. Versioning

`pyproject.toml`'s `[project].version` and `installer/pixel-agent.iss`'s
`#define MyAppVersion` must be bumped together for every release — there is no automation
tying them yet (Phase 12, CI/CD, is where that should be added). Follow semver
(`MAJOR.MINOR.PATCH`): bump `MAJOR` for a breaking change to `.env`/config compatibility,
`MINOR` for a new feature (e.g. a new phase's work), `PATCH` for a bug-fix-only release.

## Known issues found on first real build (2026-08-06 through 2026-08-08)

The first end-to-end attempt at this process on real Windows hardware surfaced five real,
previously-untested issues. All five are now fixed in the current `pixel-agent.iss` /
this doc; recorded here so the reasoning isn't lost, per this project's
`docs/DECISIONS.md` convention.

1. **`[Files]` Source paths resolved one directory too deep.** Inno Setup resolves
   relative `Source` paths against the `.iss` file's own directory (`installer\`) by
   default, not the directory `ISCC.exe` was invoked from. Every path in this script was
   written assuming project-root-relative resolution. Fixed with `SourceDir=..` in
   `[Setup]`.
2. **`OutputDir` is NOT affected by `SourceDir`** — it stays relative to the `.iss` file's
   own folder regardless. An initial fix that added `..\` to `OutputDir` (reasoning by
   analogy from fix #1) actually caused a *worse* miss, landing the compiled `.exe` one
   full directory above the project root. Fixed by setting `OutputDir=dist\installer`
   with no `..\` prefix.
3. **`README.md` was referenced at the project root, but actually lives at
   `docs/README.md`.** Fixed the `Source:` line to `docs\README.md`.
4. **The PyInstaller executable name didn't match what the `.iss` script expected.**
   `pyproject.toml` defines `pixel-gui` as the real console-entry-point name
   (`pixel-gui = "src.gui.app:main"`), which `pixel-agent.iss` already correctly
   referenced via `MyAppExeName` — but the actual PyInstaller build command used
   `--name pixel-agent` instead, producing `pixel-agent.exe`. The installer built and
   installed without error, but the Start Menu shortcut failed with "Unable to execute
   file: ...\pixel-gui.exe — CreateProcess failed; code 2." Fixed by rebuilding
   PyInstaller with `--name pixel-gui`, matching the already-correct `.iss` expectation.
5. **PyInstaller's bundled Playwright has no Chromium of its own.** See step 3 above for
   the full detail — fixed with a `PLAYWRIGHT_BROWSERS_PATH` entry written into the
   generated `.env` by `pixel-agent.iss`'s `[Code]` section, pointing at the already-staged
   `{app}\chromium`.

## What's verified vs. not, honestly

| Step | Status |
|---|---|
| `pyproject.toml` builds a valid wheel via `python -m build` | **[VERIFIED]** — built and installed, `pixel`/`pixel-gui` console commands confirmed working |
| PyInstaller bundling (`dist/pixel-gui/`) | **[VERIFIED — 2026-08-08]** — built on real Windows hardware, `pixel-gui.exe` launches correctly with the corrected `--name` |
| Tesseract/Chromium staging | **[VERIFIED — 2026-08-08]**, using `robocopy` rather than `Copy-Item -Recurse` |
| `installer/pixel-agent.iss` compiles via `ISCC.exe` | **[VERIFIED — 2026-08-08]**, after the `SourceDir`/`OutputDir`/`README.md` path fixes above |
| The installer installs and runs `pixel-gui.exe`, shows `SetupWizard` on a clean install | **[VERIFIED — 2026-08-08]** |
| A real browser-target-type task completes end-to-end from the installed build | **[VERIFIED — 2026-08-08]** — `PLAYWRIGHT_BROWSERS_PATH` fix confirmed working, not just theorized |
| Uninstall removes the app directory cleanly | **[VERIFIED — 2026-08-08]** |
| Code signing | **[NOT SET UP]** — no certificate exists; installer ships unsigned, SmartScreen warning expected |
| Desktop-target-type task from the installed (not source-run) build | **[NOT YET TESTED]** — only a browser-target-type task has been confirmed from the installer output specifically; Phase 7's desktop-path testing was against a source-run app, not this packaged one |
