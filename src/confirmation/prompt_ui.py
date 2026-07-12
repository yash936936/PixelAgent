"""
Minimal CLI/console confirmation prompt for Phase 1, matching the layout
specified in docs/DESIGN.md. Shows the proposed action, screenshot path (if
any), target account/profile, and Approve/Deny/Edit options.

Fix for a gap flagged in review: this function previously never actually
printed a screenshot path or account/profile at all, despite PHASES.md
always specifying that it should -- gate.py's prompt_fn signature simply
never carried that information. Now accepts an optional GateContext (see
gate.py) and prints both fields when present, falling back to "not
available" rather than silently omitting the line, so it's visibly obvious
in the CLI when that context wasn't supplied instead of just absent.
"""
from __future__ import annotations

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateContext, GateDecision

_HEADER = {
    Risk.EXTERNAL: "EXTERNAL ACTION — APPROVAL NEEDED",
    Risk.DESTRUCTIVE: "DESTRUCTIVE ACTION — APPROVAL + CONFIRM PHRASE NEEDED",
}


def console_prompt(step: dict, risk: Risk, context: GateContext | None = None) -> GateDecision:
    context = context or GateContext()
    header = _HEADER.get(risk, "ACTION — APPROVAL NEEDED")
    print("┌─ " + header + " " + "─" * max(1, 60 - len(header)))
    print(f"│ Action: {step.get('description', step.get('action'))}")
    print(f"│ Raw action: {step.get('action')} params={step.get('params', {})}")
    print(f"│ Screenshot: {context.screenshot_path or 'not available'}")
    print(f"│ Account/profile: {context.account_profile or 'not available'}")
    print("│")
    print("│ [A]pprove   [D]eny   [E]dit and approve")
    print("└" + "─" * 62)

    choice = input("> ").strip().lower()

    if choice == "d":
        return GateDecision(verdict="denied")

    if choice == "e":
        new_description = input("New description (blank to keep current): ").strip()
        edited = dict(step)
        if new_description:
            edited["description"] = new_description
        confirm_phrase = None
        if risk == Risk.DESTRUCTIVE:
            confirm_phrase = input('Type "CONFIRM" to proceed: ').strip()
        return GateDecision(verdict="approved", edited_step=edited, raw_user_input=confirm_phrase)

    # default / "a"
    confirm_phrase = None
    if risk == Risk.DESTRUCTIVE:
        confirm_phrase = input('Type "CONFIRM" to proceed: ').strip()
    return GateDecision(verdict="approved", raw_user_input=confirm_phrase)
