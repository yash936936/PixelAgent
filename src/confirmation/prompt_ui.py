"""
Minimal CLI/console confirmation prompt for Phase 1, matching the layout
specified in docs/DESIGN.md. Shows the proposed action, screenshot path (if
any), target account/profile, and Approve/Deny/Edit options.
"""
from __future__ import annotations

from src.brain.risk_classifier import Risk
from src.confirmation.gate import GateDecision

_HEADER = {
    Risk.EXTERNAL: "EXTERNAL ACTION — APPROVAL NEEDED",
    Risk.DESTRUCTIVE: "DESTRUCTIVE ACTION — APPROVAL + CONFIRM PHRASE NEEDED",
}


def console_prompt(step: dict, risk: Risk) -> GateDecision:
    header = _HEADER.get(risk, "ACTION — APPROVAL NEEDED")
    print("┌─ " + header + " " + "─" * max(1, 60 - len(header)))
    print(f"│ Action: {step.get('description', step.get('action'))}")
    print(f"│ Raw action: {step.get('action')} params={step.get('params', {})}")
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
