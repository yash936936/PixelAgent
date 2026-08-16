# Terms of Use

**Last updated: 2026-08-16 (Phase 17).**

Pixel Agent is a Windows desktop tool you download, install, and run yourself. There is
no hosted service, no account with the project's author, and no ongoing relationship
between you and the author once you have the software. These terms describe what the
software does, what it doesn't do, and where responsibility sits when you use it.

## What this software is

Pixel Agent takes a plain-English instruction and carries it out by controlling your
screen directly — reading pixels/UI elements, moving the mouse, clicking, typing — with
faster structured automation (Playwright, APIs) used underneath as an accelerated path
where available. Full technical detail: `docs/TRD.md` and `docs/APPFLOW.md`.

## Hard boundaries — what this software will not do, regardless of instruction

These are enforced in code, not just policy (see `context.md`, `src/brain/boundary_guard.py`):

- It will not autonomously complete graded coursework, exams, or certifications on your
  behalf. It may enroll, track progress, and summarize material — never submit graded
  answers for you.
- It will not attempt to bypass CAPTCHAs, bot-detection, or signup/verification systems
  on third-party services.
- It will not run with a "de-safetied" base model as its planning brain — the
  confirmation gate described below depends on the underlying model's own judgment
  remaining intact.

## The confirmation gate

Before taking any action classified as **External** (irreversible or affecting a system
outside your local machine — e.g. sending a message, submitting a form) or
**Destructive** (deletion, cancellation, or similarly hard-to-reverse actions), the
agent stops and asks you to approve, deny, or edit the step before proceeding. This is a
deliberate design choice (`docs/DECISIONS.md`, 2026-07-09 entry), not a limitation to be
worked around.

**Stated honestly, not oversold:** risk classification is a keyword/phrase-based guard
with an additive semantic-similarity layer (Phase 6), not a formally verified
guarantee. `docs/SECURITY_REVIEW.md` documents this and other known limitations of the
gate — including an accepted human-factors risk (repeated confirmation prompts on long
tasks can produce prompt fatigue, making a person more likely to approve without reading
carefully). You remain the last line of defense at every gated step; read what you're
approving.

## Your responsibility when using this software

You are the operator. When the agent takes an action on a website or application —
including any action you explicitly approved at the confirmation gate — that action is
being taken on your behalf, using your own accounts, credentials, and browser profile,
under your direction. This software does not create, and this document does not claim,
any legal authorization for the agent to act on a third-party service beyond whatever
authorization you already have as that service's user.

**You are responsible for knowing whether a target site or service's own Terms of
Service permit automated/agent-driven interaction.** This varies by service and is not
something this software can determine for you at runtime. See `docs/COMPLIANCE.md` for
a documented (not exhaustive, not legal advice) discussion of this question and how to
think about it for services you plan to use this agent against.

## No warranty

This software is provided "as is," without warranty of any kind, express or implied,
including but not limited to warranties of merchantability, fitness for a particular
purpose, and non-infringement. The author is not liable for any claim, damages, or
other liability arising from use of this software, including but not limited to actions
taken by the agent (whether or not you approved them at the confirmation gate), data
loss, account restrictions or bans imposed by a third-party service as a result of
automated access, or any consequence of a site's Terms of Service being violated by an
action this agent took.

This is standard open-source "as is" language, not a claim that the software is unsafe
by design — the confirmation gate, hard boundaries, and encryption-at-rest described in
`PRIVACY.md` exist specifically to reduce real risk. But no automation tool that reads
your screen and controls your mouse/keyboard can offer a legal guarantee against
mistakes, and this one doesn't pretend to.

## Data handling

See `PRIVACY.md` for the full account of what is logged, where, for how long, and what
is (and is not) encrypted at rest.

## Changes to these terms

Updated as the project's actual behavior changes, per `context.md`'s operating
instructions; every change is logged in `docs/DECISIONS.md`.
