# Debug Protocol

Run this full pass every time the codebase is updated — not just before a release. Never hand off code that
hasn't been through this pass.

## Prompt/instructions for the AI

```
You are performing a full debug pass on the pixel-agent codebase after a code update.
Go file by file, in the order listed in docs/STATUS.md. For EACH file:

1. READ the full file, not a summary or a diff — line by line.
2. Check for:
   - Broken logic (does the code do what its description in PHASES.md says it should?)
   - Syntax errors / would this file fail to import or compile?
   - Missing dependencies (is everything it imports declared in requirements.txt?)
   - Missing files (does it reference another file/module that doesn't exist yet, or a path that
     isn't created by any phase in PHASES.md?)
   - Dead/unreachable code paths
   - Silent failure points (bare except, swallowed errors, unchecked return values)
   - Any place a hard boundary from TRD.md §6 could be bypassed (this check is non-negotiable —
     flag it even if it looks like an edge case)
   - Any place risk classification (TRD.md §5) could be skipped or misapplied
3. ACTUALLY RUN what can be run: import the module, run its unit tests if present, run the
   relevant part of the app end to end for at least one happy-path case.
4. For every issue found: fix it, then re-run step 3 to confirm the fix worked.
5. Record every issue found and fixed in a "Debug Notes" entry (see format below) — do not fix
   silently and move on without a record.
6. After all files pass, update docs/STATUS.md and add a docs/DECISIONS.md entry summarizing the
   debug pass.

Do not skip a file because it "looks right." Do not stop at the first error in a file — finish
checking that file completely, then move to fixes.
```

## Debug Notes entry format
Append to the bottom of this file after each pass:

```
### [YYYY-MM-DD] Debug pass — <scope, e.g. "Phase 1 complete">
- Files checked: <list, or "all">
- Issues found:
  1. `path/to/file.py` — <issue> — <fix applied>
  2. ...
- Issues NOT fixed (external blockers, e.g. missing real API key): <list, or "none">
- Tests run: <command(s)>
- Result: <pass/fail + brief>
```

## Special checks by subsystem
- **`brain/risk_classifier.py`**: every entry in the `TRD.md §5` table must have at least one test case;
  verify no action type falls through to an implicit "Local" default.
- **`confirmation/gate.py`**: verify it's structurally impossible for an External/Destructive step to reach
  `action_router.py` without a resolved approval — trace the call path, don't just read the function.
- **`action/action_router.py`**: verify routing logic actually prefers Playwright for web targets before
  falling back to pixel control, per `TRD.md §3.4`.
- **`memory/episodic_store.py`**: verify a failed replay correctly falls back to fresh planning rather than
  silently repeating a broken plan.

---

## Debug Notes log

### [2026-07-11] Debug pass — Phase 1 complete
- Files checked: all 12 `src/` files created in Phase 1 (`config.py`, `brain/risk_classifier.py`,
  `brain/planner.py`, `brain/orchestrator.py`, `action/playwright_driver.py`, `action/action_router.py`,
  `confirmation/gate.py`, `confirmation/prompt_ui.py`, `observability/logger.py`, `main.py`) plus 3 test
  files.
- Issues found:
  1. `brain/orchestrator.py` — originally called `PlaywrightDriver` methods directly in `_execute()`,
     bypassing `ActionRouter` entirely (contradicted `TRD.md §3.4`'s routing requirement and would have
     made Phase 2's desktop-control branch require rewriting `orchestrator.py` instead of just
     `action_router.py`) — fixed by adding an `ActionRouter` param to `Orchestrator.__init__` and routing
     `_execute()` through it.
  2. `confirmation/gate.py` — initial version would have let a Destructive step through as approved even
     without the re-typed "CONFIRM" phrase if the prompt callable itself said "approved" — fixed by adding
     an explicit phrase check inside `request_approval()` so this can't be bypassed by a buggy or malicious
     `prompt_fn` implementation; added `test_destructive_requires_confirm_phrase` to lock this in.
  3. `action/action_router.py` importing `playwright_driver.py` required the `playwright` pip package to be
     installed even for router unit tests that mock the driver — confirmed intentional (import-time
     dependency), not a bug, but noted here since it's a real environment requirement, not just a "nice to
     have."
- Issues NOT fixed (external blockers): live end-to-end run against a real Chrome profile and real
  `ANTHROPIC_API_KEY` — requires `playwright install chromium` and real credentials, which live on the
  user's machine, not this build environment.
- Tests run: `pip install -r requirements.txt` (partial — chromium browser binary not installed, not needed
  for unit tests); `python -m pytest tests/ -v` — 16/16 passed; `python -c "import ..."` smoke-import of
  every Phase 1 module — all imported cleanly.
- Result: **Pass** for everything testable in this environment. Live browser + real LLM call still needs to
  be verified by the user before calling Phase 1 fully done per `PHASES.md`'s success criterion.

### [2026-07-11] Debug pass — Anthropic to Gemini swap
- Files checked: `requirements.txt`, `.env.example`, `src/config.py`, `src/brain/planner.py`, `src/main.py`
- Issues found:
  1. First implementation used `google-generativeai` (the deprecated package) — surfaced as a
     `FutureWarning` during the re-verification import check, not a silent issue. Fixed by switching to the
     current `google-genai` package (`google.genai.Client` + `google.genai.types.GenerateContentConfig`)
     and updating `requirements.txt` accordingly.
- Issues NOT fixed (external blockers): live call to the real Gemini API not verified in this environment —
  needs a real `GEMINI_API_KEY` on the user's machine.
- Tests run: `python -c "import ..."` clean-import check (no warnings) on all touched modules;
  `python -m pytest tests/ -q` — 16/16 passed (unaffected by the LLM backend swap since tests mock/avoid the
  planner's network call).
- Result: **Pass.**

