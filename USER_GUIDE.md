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
| `DEFAULT_CHROME_PROFILE` | `Default` | Chrome profile name Playwright launches |
| `PROFILES_DIR` | `./profiles` | Where Chrome profile data is stored |
| `MAX_STEPS_PER_TASK` | `40` | Step budget per task before it's aborted |
| `LOG_DIR` | `./logs` | Where trace logs and memory databases are written |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | *(empty)* | Optional — only needed if you wire in Langfuse observability later |

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

You should see all tests pass (75 as of Phase 3: 16 Phase 1 + 35 Phase 2 + 24 Phase 3).

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
