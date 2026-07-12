# Pixel Agent — Setup & Run Guide

This guide gets Pixel Agent (Phase 3: browser + desktop control + memory) running on your Windows machine
from a fresh zip extract. Follow the steps in order.

---

## 1. Requirements

- **Windows 10/11** (this build targets Windows only — see `docs/DECISIONS.md`)
- **Python 3.11+** — check with:
  ```
  python --version
  ```
- **Google Chrome** installed (used via a named Chrome profile)
- **Tesseract OCR** binary (needed for `perception/ocr.py`) — install from:
  https://github.com/UB-Mannheim/tesseract/wiki
  During install, note the install path (default is usually `C:\Program Files\Tesseract-OCR\tesseract.exe`).
- **A free Gemini API key** — get one at https://aistudio.google.com/apikey

---

## 2. Extract and enter the project

Unzip `pixel-agent-phase3.zip`, then open a terminal (PowerShell) in the extracted folder:

```
cd path\to\pixel-agent
```

---

## 3. Create and activate a virtual environment

```
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your prompt once activated.

---

## 4. Install dependencies

```
pip install -r requirements.txt
playwright install chromium
```

This installs `google-genai`, `playwright`, `python-dotenv`, `pydantic`, `pytesseract`, `pillow`,
`pyautogui`, and downloads the Chromium browser binary Playwright needs.

---

## 5. Configure environment variables

Copy the example env file and edit it:

```
copy .env.example .env
notepad .env
```

Fill in at minimum:

```
GEMINI_API_KEY=your-actual-gemini-key-here
```

Other values in `.env` already have sensible defaults and don't need to change unless you want to:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | *(required, no default)* | Your Gemini API key |
| `LLM_MODEL` | `gemini-2.5-flash` | Which Gemini model the planner calls |
| `DEFAULT_CHROME_PROFILE` | `Default` | Real on-disk Chrome profile folder name — see below, this is NOT the friendly name shown in Chrome's profile picker |
| `PROFILES_DIR` | *(your real Chrome "User Data" root)* | See below — must be the actual Chrome install's data root, not a Pixel-only folder |
| `MAX_STEPS_PER_TASK` | `40` | Step budget per task before it's aborted |
| `LOG_DIR` | `./logs` | Where trace logs and memory databases are written |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | *(empty)* | Optional — only needed if you wire in Langfuse observability later |

### Using your real, already-logged-in Chrome profile (important)

Pixel can either use a brand-new, blank Chrome profile (nothing logged in — Pixel starts every task from
scratch, including sign-ins) or your real, already-authenticated one. To use your real profile:

1. **Fully close Chrome.** Not just the window — check the system tray and Task Manager for any lingering
   `chrome.exe` processes. A running Chrome on the same profile blocks Playwright from opening it (you'll
   get a clear error telling you this if you forget).
2. Open Chrome, switch to the profile you want Pixel to use, and go to `chrome://version`. Look at
   **"Profile Path"** — the last folder in that path (e.g. `Profile 3`) is the real on-disk name, which is
   usually *not* the same as the friendly display name shown in Chrome's "Who's using Chrome?" picker
   (e.g. "Yash" might actually live in `Profile 3`, not a folder literally named "Yash").
3. Set in `.env`:
   ```
   DEFAULT_CHROME_PROFILE=Profile 3
   PROFILES_DIR=C:\Users\<you>\AppData\Local\Google\Chrome\User Data
   ```
   `PROFILES_DIR` must be that root "User Data" folder itself — **not** `...\User Data\Profile 3`. Pixel
   selects the specific profile internally via Chrome's own `--profile-directory` mechanism, the same way
   real Chrome does when you pick a profile from its own picker.

If you'd rather Pixel never touch your real logged-in sessions, point `PROFILES_DIR` at any empty folder
(e.g. `./profiles`) instead — Pixel will create and reuse its own separate, blank profile there.

---

## 6. Verify Tesseract is on PATH

Run:

```
tesseract --version
```

If this fails with "not recognized," add Tesseract's install folder to your PATH environment variable, or
set the path explicitly before running Pixel:

```
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract isn't available, Pixel still runs fine for browser-only tasks — desktop-perception steps will
just be skipped with a warning.

---

## 7. Run the test suite (recommended before first real run)

```
pip install pytest
python -m pytest -q
```

You should see all tests pass (227 as of the GUI addition: 189 from Phases 1-5 + 38 GUI/memory-facade
tests). If you don't have a display, GUI tests still run fine — they use Qt's offscreen platform
automatically via `tests/gui/conftest.py`.

---

## 8. Run Pixel

```
python -m src.main "your instruction here"
```

Example:

```
python -m src.main "open github.com and search for playwright"
```

What happens:
1. Pixel checks memory for a similar past successful task and replays it if found (Phase 3) — otherwise it
   plans fresh, step by step.
2. Each step is risk-classified (Local / External / Destructive).
3. **External or Destructive steps pause for your approval** — a console prompt shows the proposed action
   and asks you to Approve / Deny / Edit.
4. After each step, Pixel verifies the screen changed as expected; if not, it replans and retries.
5. On completion, it prints the task status and the path to the full trace log.

---

## 8b. Run Pixel (native desktop GUI)

Install the extra, GUI-only dependency (kept separate from `requirements.txt` so a CLI-only install stays
lean):

```
pip install -r requirements-gui.txt
```

Then launch the dashboard:

```
python -m src.gui.app
```

This opens a native Windows window with:
- **Task composer** at the top — type an instruction, click "Run task"
- **Live trace** (left) — every step and gate decision appears as a card in real time, color-coded per
  `docs/DESIGN.md`'s Risk-State Mapping (neutral gray = Local/auto-run, peach = External/Destructive
  needing your approval, white = final Done/Denied/Failed outcome)
- **Loop audit** (bottom-left) — running step count, LLM call count, and estimated cost for the current task
- **Memory browser** (right) — past task history, tasks flagged for review, and learned preferences,
  refreshed automatically after each run

When an External or Destructive step comes up, a modal dialog appears (matching the same
Approve/Deny/Edit — and, for Destructive, "type CONFIRM" — flow as the console prompt) and the task
pauses until you respond, exactly like the CLI. The GUI and CLI share the same underlying
`Orchestrator`/`ConfirmationGate` — it's a different front door, not different behavior.

---

## 9. Where things get stored

| Path | Contents |
|---|---|
| `./logs/task_<timestamp>.jsonl` | Full step-by-step trace log for one run |
| `./logs/episodic_memory.db` | SQLite DB of past completed tasks (for replay) |
| `./logs/semantic_memory.db` | SQLite DB of learned preferences/UI quirks |
| `./profiles/` | Chrome profile data Playwright launches with |

To reset memory and start fresh, delete the two `.db` files in `./logs/`.

---

## 10. Common issues

| Problem | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Make sure `.env` exists (not just `.env.example`) and has a real key, in the same folder you're running from. |
| `tesseract is not installed or it's not in your PATH` | Install Tesseract (step 1) and confirm `tesseract --version` works in the same terminal. |
| Playwright browser not found | Re-run `playwright install chromium`. |
| Desktop control unavailable / web-only mode warning | Expected if `pyautogui` can't reach a real display (e.g. running headless/SSH) — browser-only tasks still work. |
| Task exceeds step budget | Increase `MAX_STEPS_PER_TASK` in `.env`, or simplify the instruction. |

---

## 11. Repeating a task (to see memory/replay in action)

Run the exact same instruction twice:

```
python -m src.main "open github.com and search for playwright"
python -m src.main "open github.com and search for playwright"
```

The second run should complete with fewer Gemini planning calls, since Pixel replays the step plan from
the first successful run instead of re-planning from scratch (External/Destructive steps are still gated
for approval each time).
