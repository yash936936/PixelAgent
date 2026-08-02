# Phase 7 Checklist — First Real Live Run (Windows)

This is the first phase in the project's history meant to run against real hardware rather than mocks.
Everything below happens on **your actual Windows machine**, not in a development sandbox — nothing here
can be completed or verified remotely.

## 1. Run the pre-flight doctor tool first

```powershell
python -m src.doctor
```

This checks, without executing any real task or click:
- `GEMINI_API_KEY` is set and config loads correctly
- The Tesseract OCR binary is actually on PATH (not just `pytesseract` installed)
- Playwright's Chromium launches successfully
- A real display is available for desktop control (`pyautogui`) — reported as a warning, not a
  blocker, if missing, since browser-only tasks don't need it
- `profiles_dir`/`log_dir` are writable
- Phase 6's semantic risk layer is working correctly in this environment

Fix anything marked `✗` before continuing — `⚠` warnings only limit desktop-target-type steps, browser-only
tasks are unaffected by them.

**If Tesseract shows as installed but not found on PATH:** either add its install directory to your
system PATH, or — often simpler — set `TESSERACT_CMD` in `.env` to the full path of `tesseract.exe`
(typically `C:\Program Files\Tesseract-OCR\tesseract.exe`). See `.env.example` for the exact line to add.
Both the doctor tool and the real app read this same setting, so once the doctor check passes, the app
will find it too.

Optionally add `--live` to make one real, minimal Gemini API call and confirm the key actually works
end-to-end (this costs a trivial amount, not free, so it's opt-in):

```powershell
python -m src.doctor --live
```

## 2. Confirm your Chrome profile setup

Per `docs/DECISIONS.md`'s 2026-07-13 entry (the first bug ever caught by a live run), `PROFILES_DIR` in
`.env` must point at the real Chrome **"User Data" root**, not a Pixel-owned or profile-specific folder.
Check `chrome://version` in your real Chrome browser to confirm which profile directory name
(`DEFAULT_CHROME_PROFILE`) corresponds to your actual logged-in profile, and make sure real Chrome is fully
closed before running Pixel (a running Chrome instance locks the profile).

## 3. Start small: one browser-only task first

Per `docs/PHASES.md`'s Phase 7 scope, validate the already-partially-proven path before the untested one:

```powershell
python -m src.main "open a new tab and search for the weather"
```

Watch for:
- Does the confirmation gate correctly appear for anything External/Destructive?
- Does OCR/element detection find the right elements? (Phase 6's real-pixel harness already caught one
  real bug here — this is the first time it'll run against a *real* page, not the fixture pages.)
- Do click coordinates land where expected?

## 4. Then try a desktop-target-type task

Only after step 3 succeeds. This exercises `mouse_keyboard.py` for the first time ever in this project's
history against a real OS:

```powershell
python -m src.main "open Notepad and type a test message"
```

Watch specifically for:
- Coordinate drift if your display uses non-100% Windows scaling (this is completely unverified — the
  `tests/integration/` harness deliberately fixed its viewport to sidestep this, so this is genuinely new
  ground)
- Whether `pyautogui`'s failsafe (move mouse to a screen corner) is enough of an abort mechanism in
  practice

## 5. Capture the trace log

Every run writes to `<LOG_DIR>/task_*.jsonl`. After each task (success or failure), keep the log file —
these are the first real traces this project will have ever produced, and are exactly what Phase 9's
injection-aware signal and Phase 10's Track B data bootstrap need to mine from later.

## 6. Report back

For each task run, note:
- Did it complete, and did the result match intent?
- Any OCR misses or misclicks (compare against the actual screen)?
- Any DPI/coordinate drift?
- Did the confirmation gate fire when it should have, and only when it should have?
- Attach or share the relevant `task_*.jsonl` trace — this is what lets a second pass turn "it worked" or
  "it didn't" into an actual code fix, the same way the 2026-07-13 profile-launch bug was found and fixed
  from a real trace, not a guess.

---

**Phase 7 success criterion (from `docs/PHASES.md`):** one full task completes end-to-end on real Windows
hardware via each execution path (browser and desktop), with a real trace log to inspect for coordinate
drift, OCR misses, or timing issues that no mock could reveal.
