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

### [2026-07-09] Documentation set only — no code to debug yet
- Files checked: n/a (Phase 0, docs only)
- Issues found: none (no source code exists)
- Issues NOT fixed: n/a
- Tests run: n/a
- Result: N/A — first real debug pass occurs after Phase 1, Part 1.1 files are written.
