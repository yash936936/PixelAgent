# App Flow (User/Runtime-Facing)

This describes what actually happens, step by step, from the user's point of view when a task is run.

## 1. Instruction
User provides a natural-language task via `src/main.py` (CLI in v1):
> "Open my Work Chrome profile, find repo X on GitHub, and star it."

## 2. Planning
`brain/orchestrator.py` asks `brain/planner.py` for the next single step, using current state (nothing yet,
so: "open Chrome with profile Work").

## 3. Risk classification
`brain/risk_classifier.py` checks the step against the table in `TRD.md §5`. Opening a browser = Local,
reversible → no gate needed.

## 4. Execution
`action/action_router.py` routes the step to `action/playwright_driver.py` (web target) and it runs.

## 5. Verification
`perception/screen_diff.py` confirms Chrome opened with the right profile. If not, `brain/replanner.py`
kicks in and the orchestrator retries with a corrected step.

## 6. Loop continues
Steps 2–5 repeat for "navigate to github.com" and "search repo X" — both Local/reversible, no gate.

## 7. Confirmation gate fires
The final step, "click Star," is classified External/irreversible (visible on the user's public GitHub
activity). `confirmation/gate.py` blocks execution and `confirmation/prompt_ui.py` shows:
- The exact action
- The account/session it runs under
- A screenshot of current state
- Approve / Deny / Edit options

## 8. User decision
- **Approve** → `action_router.py` executes the click.
- **Deny** → task ends, outcome logged as user-denied.
- **Edit and approve** → user can, e.g., redirect to a different repo before it executes.

## 9. Logging
`observability/logger.py` records the full trace: every step, screenshot reference, gate decision, and
final outcome, timestamped.

## 10. Memory write
Once memory exists (Phase 3), `memory/episodic_store.py` saves (instruction, step plan, outcome) so a
near-identical future instruction can attempt replay instead of full re-planning.

## Failure path
At any step, if execution fails (element not found, page didn't load, etc.), `brain/replanner.py` gets the
failure + current screen state and proposes a corrected step. If failures repeat past a retry limit, the
task ends and is reported to the user as failed, with the partial trace available in the logs.

## Cancellation
The user can cancel at any confirmation prompt, or interrupt the process entirely; nothing further executes
once cancelled, and the partial trace is still logged.
