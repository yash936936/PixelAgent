# SECURITY_REVIEW.md — Phase 16

**Status: first pass complete, 2026-08-12.** This is a fresh-eyes review conducted by
Claude (not the same instance/session that wrote most of the code under review, though
with full visibility into `docs/DECISIONS.md`'s history) — the closest approximation to
an independent review available without a third-party auditor, per `docs/PHASES.md`'s
own acknowledgment that this project's `eval/` harness is "a good regression suite, not
a security audit."

**Scope caveat, stated upfront**: this review is bounded by what's actually been shown
across this project's session history and documentation. It is not a review of source
files this reviewer has never seen in full (e.g. `src/action/action_router.py`,
`src/perception/ocr.py`, `src/memory/episodic_store.py`'s complete implementation) —
findings below are flagged as either "confirmed" (verified against real code/output
seen directly) or "based on documented behavior" (inferred from `docs/DECISIONS.md`'s
own description, not independently re-verified against source).

---

## 1. Confirmed finding: a real credential leaked into git history

**Severity: was Critical; now Resolved, with a residual process gap.**

During this session, a real `GEMINI_API_KEY` was found committed in plaintext inside
two test files (`tests/test_setup_wizard_logic.py`, `tests/gui/test_setup_wizard.py`),
used as fixture data for testing `looks_like_a_real_api_key()`. This was not a
placeholder — cross-referencing against the key actually present in a real installed
`.env` confirmed it was the user's genuine, live key.

**What happened, for the record:**
- The key was caught before the push succeeded, by GitHub's own push-protection
  scanning (`GH013: Repository rule violations found... Push cannot contain secrets`).
- The user rotated the key.
- The commit was amended in place (this repo had only one commit at the time, so a
  simple `git commit --amend` was sufficient — no `filter-repo`/history rewrite of a
  deep history was needed).
- Verified clean via `git log --all -p | grep -c "<key-prefix>"` returning `0` before
  the next push.

**What this confirms about the underlying risk, independent of this one incident**:
`.env`-based credential storage (this project's only mechanism for `GEMINI_API_KEY`)
has no built-in safeguard against a human accidentally pasting a real key into a test
fixture, a docs example, or a debugging session transcript. GitHub's push protection
caught it this time — that is a safety net belonging to GitHub, not to this project's
own design, and it only fires on a `git push`, not on `git commit`, not on a key
copy-pasted into a chat log, a shared terminal, or a screenshot (this session itself
has several screenshots with a real, since-rotated key visible on screen).

**Residual gap, not yet addressed**: there is no `.gitignore`/pre-commit hook in this
repo specifically scanning for high-entropy strings resembling API keys before a commit
is even made — the only protection is GitHub's server-side scan, which is: (a) a single
point of failure, (b) specific to GitHub (would not catch this on a `git push` to a
different host, or an internal transfer via `git bundle`/`git format-patch`), and (c)
after-the-fact — the key still touched local history and, in this specific case, was
also visible in the plaintext conversation transcript with an AI assistant, which is
its own, separate exposure surface entirely outside git's boundary.

**Recommendation**: add a local pre-commit hook (e.g. `detect-secrets`, `gitleaks`, or
even a minimal grep-based regex check for `AQ\.` — the actual prefix format of a real
Gemini key per what was observed this session) that runs before every local commit, not
just relying on GitHub's server-side catch. This is a cheap, high-value addition given
this project has now had one real, confirmed near-miss.

---

## 2. Confirmed finding: `.env`'s plaintext credential storage remains explicitly
   out of scope, and this review agrees that's a defensible call — with one caveat

Per `docs/DECISIONS.md`'s Phase 8 design-decision entry (2026-08-02), `.env`'s
plaintext `GEMINI_API_KEY` was explicitly and deliberately excluded from that phase's
encryption-at-rest work, with the stated reasoning that protecting the episodic/
semantic memory stores while leaving `.env` in the clear "one file over" would be
security theater without a matching fix, and that OS-level credential storage (Windows
Credential Manager) would need a larger config-loading redesign not attempted at the
time.

**This review's assessment**: the reasoning holds, and revisiting it now that Phase 8
is complete is reasonable — deferring is not the same as ignoring, and the original
entry states this honestly rather than glossing over it. **The caveat**: given finding
#1 above (a real key genuinely did leak, via a different vector than `.env` itself, but
demonstrating that "this key is sensitive" awareness clearly existed and the leak still
happened), the actual residual risk of `.env`'s plaintext storage is no longer purely
theoretical for this project — it's now been shown, empirically, that credential
mishandling is a real failure mode humans using this project hit in practice, not just
a hypothetical worth a paragraph in a design doc.

**Recommendation**: Phase 16 is a reasonable point to at least scope (not necessarily
implement) the Windows Credential Manager migration Phase 8 deferred — a scoping-only
follow-up entry, mirroring how Phase 8 itself started with a design-decision-only entry
before implementation.

---

## 3. Based on documented behavior: the confirmation-gate trust boundary

Per `docs/DECISIONS.md`'s history, this is the single most load-bearing safety
mechanism in the project, and it has already been through two real, confirmed
close-calls, both caught by live use rather than by design review:

- **2026-08-01**: the CLI's `console_prompt()` silently treated any unrecognized input
  (including a plain typo) as approval — the single most safety-critical possible bug
  in a human-in-the-loop gate, since it inverts the entire trust model from
  "approval required" to "anything except an exact denial is approved." Confirmed fixed
  (looping re-prompt, GUI path confirmed to never have had this bug since it defaults
  to denied).
- **2026-08-01**: `AUTO_APPROVE_EXTERNAL` was added per explicit user request, and the
  design correctly keeps `Risk.DESTRUCTIVE` unconditionally excluded from it regardless
  of the setting — this reviewer confirms that design boundary is the right one to hold
  as non-negotiable, and that it's implemented as a hard exclusion in code (per
  `docs/DECISIONS.md`'s description) rather than a default that could be silently
  overridden by a future config change.

**Independent observation, not previously flagged in `DECISIONS.md`**: the
confirmation gate's trust model assumes the human reading the prompt is paying
attention and understands what they're approving. Nothing in this project's documented
design addresses **prompt fatigue** — a human who has approved 40 External-risk
prompts in a row for a long-running task may click through the 41st without reading it
carefully, especially with `AUTO_APPROVE_EXTERNAL` already showing this project is
willing to trade some safety for reduced friction. This is a human-factors risk, not a
code bug, and this review does not have a concrete fix to propose beyond flagging it —
but it's worth being aware of as a real, not-yet-mitigated risk class distinct from
anything the eval harness measures.

---

## 4. Based on documented behavior: the boundary guard's fundamental limits

`docs/STATUS.md`'s own "Known gaps" section already states this honestly: the hard
boundary guard is keyword/phrase-based as its primary mechanism, with an additive
semantic layer (Phase 6) that improved but did not solve the underlying gap (73%
overall on the adversarial eval as of 2026-08-01, well short of the ≥0.95 threshold
`eval/README.md` sets for a genuinely trustworthy deployment gate).

**This review's assessment**: the honesty here is a real strength — this project does
not claim a stronger guarantee than it can back up. The genuine remaining risk is that
`RISK_MODEL_BACKEND=local` (the trained-model path meant to close this gap) has never
been trained, per Phase 10's honest zero-result entry — meaning the actual boundary
enforcement running in any real deployment today is still the original keyword +
semantic-similarity floor, not the stronger mechanism this project's own roadmap
anticipated. **This is fine as long as it stays documented and visible** (which it
currently is, consistently, across `STATUS.md`, `PHASES.md`, and the eval `README.md`)
— the risk is specifically if that context gets lost in a future summary/handoff and
someone reasonably assumes the boundary guard is stronger than it currently is.

---

## 5. Confirmed finding: the injection-signal check (Phase 9) is correctly scoped,
   but its stated limitation is worth re-emphasizing here

Per `docs/DECISIONS.md`'s Phase 9 entry, `check_injection_signal()` only inspects a
step's own description/params — the planner's paraphrase of what it read on screen —
not the actual raw page content the planner was looking at. This means a sufficiently
subtle injection attack, one where the planner's own paraphrase doesn't happen to echo
injection-shaped language even though the source page content did, would be invisible
to this check entirely, not just imperfectly caught.

**This review's assessment**: this is accurately and honestly scoped in the existing
docs ("visibility, not verdict" is a fair characterization) — flagging it here mainly
to note that page-text extraction and diffing (mentioned as a natural future extension
in the Phase 9 entry) would meaningfully change this from "usually visible" to
"structurally guaranteed visible," and given how central this project's confirmation
gate is to its whole safety model, that gap is worth prioritizing over some other open
items on the roadmap.

---

## 6. Based on documented behavior: encryption-at-rest's real-world guarantee

Phase 8's DPAPI implementation is confirmed working on real hardware (per the
2026-08-02 confirmation entry). This review's read of the stated threat model (a local
account without this Windows user's login, or a lost/stolen/resold drive) is accurate
and honestly scoped — DPAPI genuinely does defend against exactly those two scenarios
and does not claim to defend against more.

**Observation not previously stated explicitly**: DPAPI-encrypted data is only as safe
as the Windows user account it's tied to. If that Windows account's own login
credential is weak, or if the machine has other malware with SYSTEM/admin access
already running under that same session, DPAPI provides no protection at all (this is
inherent to how DPAPI works, not a flaw in this project's use of it) — worth a single
sentence in `docs/SECURITY.md`/`PRIVACY.md` (Phase 17, not yet written) making this
explicit for an end user who might otherwise read "encrypted" as a stronger guarantee
than it is.

---

## 7. Confirmed finding, positive: the "fail loud, not silent" pattern is genuinely
   consistent across this codebase

Cross-referencing multiple entries in `docs/DECISIONS.md` (the confirmation-gate
silent-approve fix, `OperationalLimitExceeded`'s deliberate distinctness from other
exceptions, verification failures now logged rather than silently swallowed, the
boundary guard's non-negotiable hard-stop design) shows a real, consistently-applied
engineering discipline rather than a one-off fix. This is worth stating positively in
a security review, not just cataloging gaps — a codebase that has internalized this
pattern is structurally less likely to accumulate new silent-failure bugs going
forward, even in code this review hasn't directly seen.

---

## Summary table

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Real credential leaked to git history | Was Critical | Resolved; process gap (no pre-commit secret scanning) remains |
| 2 | `.env` plaintext storage, deferred from Phase 8 | Medium | Deferred, defensibly; now has real (not just theoretical) supporting evidence to revisit |
| 3 | Confirmation-gate prompt fatigue | Low/Unaddressed | Flagged, no fix proposed |
| 4 | Boundary guard's real deployed strength vs. roadmap's intended strength | Medium | Honestly documented; risk is context loss over time |
| 5 | Injection-signal check's structural blind spot (paraphrase-only) | Medium | Honestly documented; a real future-work candidate |
| 6 | DPAPI's guarantee is tied to Windows account security | Low | Not yet stated explicitly in end-user-facing docs |
| 7 | "Fail loud" pattern consistency | — (positive) | Genuine strength, worth preserving as a norm |

## Recommended next actions, in priority order

1. Add a local pre-commit secret-scanning hook (finding #1's residual gap) — cheap,
   high-value, directly motivated by a real incident this session.
2. Scope (design-decision-only, Phase-8-style) a Credential Manager migration for
   `.env` (finding #2).
3. Add one explicit sentence to future user-facing docs (Phase 17) about DPAPI's
   actual guarantee boundary (finding #6) — trivial to add, meaningfully reduces a
   false sense of security.
4. Longer-term: page-text extraction/diffing for the injection-signal check
   (finding #5) and continued progress toward Track B's trained risk model (finding
   #4) — both already on this project's own roadmap, this review just adds weight to
   prioritizing them.

This review does not itself constitute `docs/PHASES.md`'s full Phase 16 success
criterion — that criterion calls for findings to be "triaged and either fixed or
explicitly accepted with reasoning recorded in `docs/DECISIONS.md`." This document is
the findings; the triage/accept-or-fix decision for each is a follow-up the project
owner should make explicitly, not something this review can decide unilaterally.
