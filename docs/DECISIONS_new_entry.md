### [2026-08-08] First real Windows installer build completed end-to-end — five real bugs
  found and fixed, first fully successful task from an installed (not source-run) build
- **Type:** Overwrite (multiple)
- **File(s) affected:** `installer/pixel-agent.iss`, `docs/RELEASE.md`.
- **What changed:** Continuing directly from the 2026-08-06 entry (which fixed
  `SourceDir`/`OutputDir` and the `Copy-Item`→`robocopy` staging issue but left the
  Inno Setup compile itself unconfirmed), the user completed a full, real build-install-
  run-uninstall cycle on their actual Windows machine for the first time in this
  project's history. Five real, previously-untested issues surfaced, all now fixed:
  1. **`README.md` `Source:` path was wrong.** Referenced the project root, but the file
     actually lives at `docs/README.md`. `ISCC.exe` failed with `Source file
     "...\README.md" does not exist.` Fixed: `Source: "docs\README.md"`.
  2. **PyInstaller's `--name` flag didn't match `pixel-agent.iss`'s `MyAppExeName`.**
     `pyproject.toml`'s real console-entry-point name is `pixel-gui`
     (`pixel-gui = "src.gui.app:main"`), which the `.iss` script had already correctly
     referenced — but the PyInstaller build command used `--name pixel-agent`, producing
     `pixel-agent.exe`. The installer built and installed without any compile-time error,
     but the Start Menu shortcut failed at launch: `Unable to execute file:
     ...\pixel-gui.exe — CreateProcess failed; code 2. The system cannot find the file
     specified.` This is a genuinely dangerous failure mode for a release process — a
     "successful" build that silently produces a broken shortcut. Fixed by rebuilding
     PyInstaller with `--name pixel-gui`, matching the `.iss` file's (correct, already
     cross-checked against `pyproject.toml`) expectation, rather than changing the `.iss`
     to match the wrong build command.
  3. **PyInstaller's bundled Playwright ships with no Chromium binary of its own.** After
     fixing #2, the app genuinely launched and showed the dashboard, but the first real
     browser-target-type task crashed with `Executable doesn't exist at
     ...\_internal\playwright\driver\package\.local-browsers\chromium-<version>\
     chrome-win\chrome.exe`. Root cause: Playwright always expects a Chromium install at
     a separate, OS-level cache path (or wherever `PLAYWRIGHT_BROWSERS_PATH` points) —
     nothing in the PyInstaller bundling step or the installer's existing Chromium
     staging (`installer/staging/chromium/` → `{app}\chromium\`) ever told the bundled
     Playwright runtime to look at that staged copy instead of its normal (empty, in a
     fresh install) cache. Fixed by extending `pixel-agent.iss`'s existing `[Code]`
     section (which already pre-seeds `TESSERACT_CMD` in a fresh `.env`) to also write
     `PLAYWRIGHT_BROWSERS_PATH={app}\chromium` whenever the `chromium` component is
     selected — the app already loads `.env` into its process environment on startup
     (the same mechanism `GEMINI_API_KEY` relies on), and Playwright itself reads
     `PLAYWRIGHT_BROWSERS_PATH` from the OS environment at launch time, independently of
     `config.py` — so no PyInstaller or Python-level change was needed, only the
     installer's own `.env`-seeding logic.
  4. **The `gemini-2.5-flash` default model is dead for new API users.** Unrelated to
     packaging, but found during this same live-run cycle: `config.py`'s
     `llm_model: str = "gemini-2.5-flash"` default (and `.env.example`'s matching line)
     now returns a hard `404 NOT_FOUND` — Google has discontinued it for new users
     (confirmed via Google's own release notes: 2.5-series models scheduled for full
     shutdown 16 October 2026, already unavailable to new callers before that date). The
     SetupWizard's generated `.env` has no `LLM_MODEL` line at all (the wizard only
     collects the API key and Chrome profile), so every fresh install silently inherits
     the dead hardcoded default with no way to override it short of hand-editing the
     installed `.env`. Worked around for this session by manually adding
     `LLM_MODEL=gemini-3.5-flash-lite` to the installed `.env` (confirmed GA and current
     per Google's own docs) — **not yet fixed at the source** (`config.py`'s default and
     `.env.example`'s line 4 both still say `gemini-2.5-flash`; see "Impacts" below).
  5. **Confirmed, not a bug:** an earlier SetupWizard test that appeared to skip straight
     to the Dashboard instead of showing the wizard was traced to a leftover `.env` from
     a prior install attempt on the same machine, not a real wizard-gating bug — the
     `needs_setup()` logic worked correctly once tested against a genuinely clean
     uninstall-then-reinstall.
- **Why:** Direct continuation of the 2026-08-06 entry's live-build attempt — that entry
  got the Inno Setup script compiling; this session took the resulting installer all the
  way through install, first real task execution, and uninstall for the first time,
  surfacing issues invisible to a compile-only check (same pattern as every Phase 7 live-
  run entry: real bugs only a real run finds).
- **Impacts:** `docs/RELEASE.md`'s verified/unverified table updated — PyInstaller
  bundling, Inno Setup compilation, install/SetupWizard/uninstall, and a real
  browser-target-type task from the *installed* build are now all **[VERIFIED]** rather
  than assumed. **Two items explicitly NOT yet done, flagged rather than assumed clean:**
  (a) `config.py`'s `llm_model` default and `.env.example` line 4 still point at the now-
  dead `gemini-2.5-flash` — every future fresh install will hit the same 404 until this
  is fixed at the source, not just patched on one installed machine; this should be a
  follow-up code change, not another `.iss`/doc-only entry. (b) only a browser-target-type
  task has been confirmed against the installed (packaged) build specifically — Phase 7's
  desktop-path testing (`mouse_keyboard.py`) was against a source-run app, and has not
  been re-confirmed from this installer output.
