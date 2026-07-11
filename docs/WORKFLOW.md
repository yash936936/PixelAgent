# Development Workflow (Build Lifecycle)

This is the developer-facing lifecycle — how the codebase actually gets built, run, and maintained,
distinct from `APPFLOW.md` which is the end-user runtime flow.

## 1. Setup
```
git clone <repo>
cd pixel-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## 2. Configure
Copy `config.example.py` (created in Phase 1) to `config.py` (or set env vars, per whichever
`src/config.py` implements) and set:
- LLM API key/model
- Default Chrome profile name
- Max-step budget
- Log directory path

## 3. Build order
Follow `PHASES.md` in order — do not start Phase 2 files before Phase 1's success criterion is met, since
later phases' orchestrator updates assume the earlier loop already works. Each phase/part lists its exact
files.

## 4. Before writing or overwriting any file
1. Check `docs/STATUS.md` for that file's current status.
2. Add an entry to `docs/DECISIONS.md` (see template there) describing the change before/alongside making it.
3. Make the change.
4. Update `docs/STATUS.md` for that file.

## 5. Run
```
python src/main.py "your instruction here"
```

## 6. Test
- `tests/` mirrors `src/` structure (e.g. `tests/brain/test_planner.py`)
- Run with `pytest` before considering any phase complete
- At minimum: unit tests for `risk_classifier.py` (every risk class correctly identified) and
  `action_router.py` (correct routing between Playwright and pixel control)

## 7. Debug pass
Run the full protocol in `docs/DEBUG.md` any time the codebase is updated — not just at the end of a phase.

## 8. Deploy/package
Local-first tool — "deploy" means packaging into a runnable local install (e.g. a Windows executable or a
documented Python environment setup). No cloud deployment step exists for v1 per scope boundaries.

## 9. After each merge/update
1. Re-run `DEBUG.md` protocol.
2. Update `docs/STATUS.md`.
3. Confirm `docs/DECISIONS.md` has a matching entry.
4. If the change affects app-facing behavior, update `docs/APPFLOW.md` to match reality (never let it
   describe an idealized version of the code).
