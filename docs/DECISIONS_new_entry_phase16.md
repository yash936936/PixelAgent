### [2026-08-12] Phase 16 — independent security review, first pass
- **Type:** New (review + eval expansion, no source code changes)
- **File(s) affected:** `docs/SECURITY_REVIEW.md` (new), `eval/adversarial_cases.jsonl`
  (append-only additions proposed, not yet merged — see below).
- **What changed:** A fresh-eyes security review per `docs/PHASES.md`'s Phase 16 scope.
  Seven findings, summarized: (1) a real credential leak this session itself caused and
  resolved, with a residual process gap (no local pre-commit secret scanning) flagged
  as the highest-priority actionable item to come out of this review; (2) `.env`'s
  plaintext credential storage, deliberately deferred at Phase 8, revisited given
  finding #1 now provides real (not just theoretical) supporting evidence; (3) an
  unaddressed human-factors risk (confirmation-gate prompt fatigue on long tasks), (4)
  the gap between the boundary guard's currently-deployed strength (keyword + semantic
  floor) and the stronger trained-model mechanism the roadmap anticipates but Phase 10
  never delivered (honest zero result); (5) the injection-signal check's structural
  blind spot (inspects the planner's paraphrase, not raw page content); (6) DPAPI's
  actual guarantee boundary not yet stated explicitly in any user-facing doc; (7) a
  positive finding — the "fail loud, not silent" pattern is genuinely consistent across
  this codebase's history, not a one-off fix. Twelve new adversarial eval cases
  proposed (`eval/adversarial_cases_ADDITIONS.jsonl.md`), deliberately written adjacent
  to the 11 real failing cases surfaced by this session's own CI run rather than
  generic additions, covering `evasive_destructive`/`boundary_evasion`/
  `evasive_external`/`local`/`prompt_injection`/`benign_but_tricky` gaps specifically.
- **Why:** Directly implements `docs/PHASES.md`'s Phase 16 file table and success
  criterion. The credential-leak finding in particular makes this review materially
  more grounded than a purely hypothetical exercise would have been — it's reviewing a
  codebase that has already had one real, live security incident during its own
  development, not just theorizing about what could go wrong.
- **Impacts:** `docs/PHASES.md`'s Phase 16 success criterion ("a documented security
  review exists, findings are triaged and either fixed or explicitly accepted with
  reasoning recorded") is **partially met**: the review and findings exist and are
  documented, but the triage step (deciding fix-vs-accept for each of the 7 findings)
  has NOT yet happened — that's a deliberate next action for the project owner, not
  something this review decided unilaterally. The 12 new eval cases have NOT been
  merged into the real `eval/adversarial_cases.jsonl` or run — they need the real
  file's current schema/highest-ID confirmed first (see the additions file's own note).
  Recommended immediate next step: triage finding #1 (add a pre-commit secret scanner)
  first, since it's cheap, high-value, and directly motivated by a real incident rather
  than a hypothetical one.
