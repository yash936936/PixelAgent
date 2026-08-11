# installer/pixel-agent.iss — REAL bug found by CI, not a CI-only issue

## What CI found

```
Error on line 99 in D:\a\PixelAgent\PixelAgent\installer\pixel-agent.iss:
No files found matching "D:\a\PixelAgent\PixelAgent\dist\pixel-agent\*"
```

## Root cause

PyInstaller's `--onedir` mode names its output folder after whatever `--name` you
pass it. Your build command is:

```powershell
pyinstaller --name pixel-gui --windowed --onedir --noconfirm ...
```

That produces `dist/pixel-gui/`, not `dist/pixel-agent/`. But `pixel-agent.iss`'s
`[Files]` section (line 99, or wherever it sits in your current file) still says:

```ini
Source: "dist\pixel-agent\*"; DestDir: "{app}"; ...
```

This is a leftover from BEFORE the `pixel-gui` rename fix (2026-08-08 session) — when
that fix changed the PyInstaller command's `--name` flag, the `.iss` file's `Source`
path was never updated to match. **This bug has been sitting in your installer script
this whole time.**

## Why it worked on your local machine but not on CI

Your local `dist/` folder almost certainly still had a stale `dist/pixel-agent/`
directory sitting on disk from an EARLIER build attempt (before the `--name pixel-gui`
fix), left over from before you discovered and fixed the executable-naming bug.
`ISCC.exe` found and packaged those old, stale files successfully — meaning **your
last "verified working" installer build may have actually shipped the OLD,
wrongly-named `pixel-agent.exe` build artifacts**, not the corrected `pixel-gui`
ones, even though the compile succeeded and the resulting installer worked (because
the stale folder happened to still contain a working, if outdated, build).

CI starts from a completely clean checkout every time — no stale `dist/pixel-agent/`
folder exists, so it correctly failed instead of silently masking the mismatch.

## The fix

In your real `installer/pixel-agent.iss`, find:

```ini
Source: "dist\pixel-agent\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
```

Replace with:

```ini
Source: "dist\pixel-gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
```

## Recommended follow-up, not optional

1. **Delete your local `dist/` folder entirely** and do one fully clean local rebuild
   (`pyinstaller --name pixel-gui ...` → `robocopy` staging → `ISCC.exe`) to confirm
   the fixed `.iss` actually works from a clean state, the same way CI now does. Don't
   trust the "it worked" from earlier tonight — that verification may have been
   against stale files.
2. Re-run the full smoke test from `docs/RELEASE.md` step 5 against this freshly
   built installer, including the browser-task check — to confirm the actually-shipped
   build (this time genuinely built from `dist/pixel-gui/`) still works end to end.
3. This is worth its own `docs/DECISIONS.md` entry — a real bug that had been silently
   masked by local state, only caught once CI ran against a clean checkout. That's
   exactly the kind of thing CI exists to catch, and worth recording as such.
