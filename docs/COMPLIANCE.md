# Compliance — automated access vs. target sites' Terms of Service

**Status: Documented answer per Phase 17's success criterion (2026-08-16). This is not
legal advice — it's an honest, documented answer to "what happens legally if this agent
takes an action a site's ToS prohibits," written by the project's engineer, not a
lawyer.**

## The core question

Pixel Agent controls a real browser (via Playwright, using your real Chrome profile) or
the real OS-level mouse/keyboard to interact with websites and applications on your
behalf. Many websites' Terms of Service restrict "automated access," "bots," or
"scraping" in some form. This document is the honest answer to: what happens when this
agent takes an action on a site whose ToS prohibits that kind of access?

## The short, honest answer

**It's the same legal position as if you'd written a browser automation script
yourself and run it against your own account on that site — because that's
functionally what's happening.** This project does not have, and does not claim to
have, any special legal standing that changes that. Whether a specific action is a ToS
violation depends entirely on the specific site's specific terms, which this project
cannot audit for you in advance, because it doesn't know in advance which sites you'll
point it at.

**This is a real liability question the moment this runs on behalf of anyone other than
the original developer against their own accounts** — using this agent against your own
accounts, for your own purposes, is a materially different situation from operating it
on someone else's behalf or against accounts you don't own, and the honest answer to
"is this okay" gets less clear the further you move from the first case.

## What kind of automation is likely to trip ToS restrictions

Speaking generally, not about any specific site (site ToS documents change, and this
project has not reviewed every possible target site — see "What this document does not
do" below):

- **Bot/automation clauses.** Many ToS documents (social platforms, e-commerce,
  ticketing, financial services in particular) explicitly prohibit "automated,"
  "scripted," or "bot" access to the service, sometimes regardless of whether a human is
  supervising it.
- **Rate/volume restrictions.** Even sites without an outright automation ban often cap
  request volume or action frequency in ways a fast automated agent could exceed even
  while performing actions a human could do manually.
- **Account-sharing/credential-use clauses.** Some services' terms restrict how
  authentication credentials may be used, which can implicate an agent acting through a
  saved browser session.
- **CAPTCHA/bot-detection bypass.** This project's own hard boundaries (`context.md`,
  `src/brain/boundary_guard.py`) already refuse to bypass CAPTCHAs or bot-detection —
  this is the one category where the code itself, not just this document, takes a
  position: the agent will not attempt to circumvent a site's own bot-detection
  mechanism, regardless of instruction.

## What this project does to reduce (not eliminate) this risk

- **Hard boundary against CAPTCHA/bot-detection bypass and signup/verification bypass**
  — enforced in code, not policy, per `context.md`.
- **The confirmation gate** stops before any External or Destructive action and asks
  you to approve it — giving you, the account holder, a chance to recognize and decline
  an action you know or suspect would violate a site's terms, before it happens.
- **This agent controls your real, authenticated browser session** rather than
  scraping anonymously or forging requests — it is, mechanically, closer to "a human
  using their own logged-in browser, faster" than to a scraper impersonating a browser
  it isn't. That distinction matters for some ToS language (many bot clauses target
  unauthenticated/anonymous scraping specifically) but not all of it, and doesn't
  change the analysis for services whose terms restrict any automation, authenticated
  or not.

## What this document does not do

- It does not review any specific target site's Terms of Service. Doing so
  meaningfully would require re-doing this analysis per site, since ToS language and
  enforcement posture vary widely and change over time — a generic answer here would be
  false confidence, not a real review.
- It is not legal advice, and does not substitute for consulting a lawyer if you plan
  to operate this agent in a context where ToS violation could carry real consequences
  (e.g. commercial use, use against accounts you don't personally own, or use at a
  volume/scale that draws a platform's attention).
- It does not claim any specific action this agent might take is or isn't a violation
  of any specific site's terms — that determination depends on facts (the site, the
  action, the terms in force at the time) this document cannot know in advance.

## Practical guidance, stated plainly

1. **Read the ToS of any service you plan to point this agent at**, specifically for
   language about automated/bot/scripted access, before relying on this agent against
   that service.
2. **Prefer using this agent against your own accounts, for your own purposes.** This is
   the case the confirmation gate and hard boundaries were designed around, and the case
   with the clearest, least ambiguous legal footing.
3. **Treat the confirmation gate as a real checkpoint, not a formality** — if a step
   the agent proposes looks like it might cross a line you're not sure about, deny or
   edit it rather than approving by habit.
4. **If you plan to operate this agent on behalf of someone else, or against a service
   in a commercial/high-volume context, get real legal advice specific to that
   service's terms** — this document is deliberately not a substitute for that.

## Phase 17 success criterion — how this document meets it

Per `docs/PHASES.md`'s Phase 17: "a documented answer (not necessarily 'yes it's fine
everywhere') to 'what happens legally if this agent takes an action a site's ToS
prohibits.'" This document is that answer: functionally the same legal position as
running your own automation script against your own account, materially clearer for
personal use against your own accounts than for third-party or commercial use, not
audited per-site, and not a substitute for real legal advice in higher-stakes contexts.
