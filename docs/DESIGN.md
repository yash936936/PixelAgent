# Design System — "Steep" (adopted 2026-07-12)

**This replaces the old console-only color scheme.** Every future GUI surface for Pixel Agent —
confirmation prompts, dashboard, trace viewer, memory browser — is built from this system and **only**
this system. The raw machine-readable source of truth lives alongside this file:

- `docs/design-tokens/tokens.json` — full token set (colors, typography, spacing, radius, shadow, surface)
- `docs/design-tokens/variables.css` — the same tokens as plain CSS custom properties
- `docs/design-tokens/theme.css` — the same tokens as a Tailwind v4 `@theme` block
- `docs/design-tokens/DESIGN_source.md` — the full original style reference (components, imagery, layout,
  agent prompt examples) this file is distilled from

This file is the narrative/usage layer on top of those; when in doubt, the token files are authoritative
for exact values, this file is authoritative for *when/why* to use which token in Pixel Agent specifically.

## Identity
Steep renders the product as editorial, not as a dashboard shell: serif display headlines float over a
near-monochrome white canvas, one warm peach accent punctuates an otherwise achromatic system, and product
UI (task traces, confirmation cards, memory tables) is presented as floating white artifacts around the
content rather than nested in dark chrome. Quiet, weightless, generous whitespace, pill-shaped controls.

## Tokens — Colors

| Name | Value | Token | Role |
|---|---|---|---|
| Ink Black | `#17191c` | `--color-ink-black` | Primary text, filled button background — the only dark surface in the system |
| Paper White | `#ffffff` | `--color-paper-white` | Page canvas, button text, elevated card surfaces |
| Mist Gray | `#f2f2f3` | `--color-mist-gray` | Card surfaces, secondary backgrounds, input fills |
| Fog White | `#fafafb` | `--color-fog-white` | Alternating section backgrounds, hover surfaces |
| Slate Gray | `#777b86` | `--color-slate-gray` | Link color, muted helper text |
| Ash Gray | `#979799` | `--color-ash-gray` | Tertiary labels, tags |
| Smoke Gray | `#a3a6af` | `--color-smoke-gray` | Placeholder text, disabled labels |
| Blush Peach | `#fbe1d1` | `--color-blush-peach` | **The only chromatic surface in the system** — accent/attention cards |
| Sienna Brown | `#5d2a1a` | `--color-sienna-brown` | Text/stroke on peach surfaces, chart-line stroke |

## Typography
- **Signifier** (serif, weight 400 only, all sizes) — display/headline use only: 44px / 64px / 90px.
- **Sohne** (sans, weights 400/430/450/480/500) — everything else: 14–26px.
- Full type scale, letter-spacing, and line-heights: see `docs/design-tokens/tokens.json` -> `typography`.

## Spacing, Radius, Shadow
- Base unit 4px; scale 4/8/12/16/20/24/28/32/40/64/80/96/124/128/160px.
- Structural radii: **9999px** on all buttons, **24px** on all content cards, 12px images, 16px inputs,
  20px elevated/floating artifacts.
- Shadow is reserved for floating product artifacts only — see "Elevation" below. Content cards
  (Neutral, Accent Peach) never carry a shadow.

## Components (mapped to Pixel Agent's actual GUI surfaces)

| Steep component | Used for, in Pixel Agent |
|---|---|
| Pill Button — Filled (`#17191c` bg) | Primary actions: "Approve", "Run task" |
| Pill Button — Ghost (`#17191c` border, transparent) | Secondary actions: "Deny", "Cancel" |
| Text Link with Arrow | "View full trace ->", "See past runs ->" |
| Neutral Card (`#f2f2f3`, 24px radius, no shadow) | Task history rows, settings panels, memory fact list |
| Accent Peach Card (`#fbe1d1` bg, `#5d2a1a` text) | **Reserved — see Risk-State Mapping below, not decorative use** |
| Floating Product Artifact (white, 20px radius, subtle shadow) | The live screenshot preview, the confirmation-gate card itself, stat/trace cards |
| Input / Composer | The task-instruction input box ("What should Pixel do?") |
| Stat Card with Chart | LoopAudit summary (step count, LLM calls, est. cost) per `docs/CODE_LOGIC.md §9` |
| Avatar Bubble | Not used — no multi-user presence in this product |
| Tag / Category Label | Risk-class label chip (see below), task-status chip (done/error/denied) |

## Risk-State Mapping — supersedes the old amber/red/green scheme

The Steep system is **deliberately near-monochrome with a single chromatic accent** (peach), so the
previous design's three distinct risk colors (amber/red/green) don't exist here. Per this project's own
accessibility rule (never rely on color alone, always pair with a text label — see `TRD.md §5`), risk state
is carried primarily by **label text + card weight**, with peach reserved as the one "this needs your
attention" signal, differentiated by ink color:

| Risk class | Card surface | Ink / border | Label (always shown, never color-only) |
|---|---|---|---|
| **Local** (auto-executes) | Neutral Card `#f2f2f3` | `#17191c` text | "Local — running automatically" |
| **External** (needs approval) | Accent Peach Card `#fbe1d1` | `#17191c` text, `#17191c` 1px border | "EXTERNAL — APPROVAL NEEDED" |
| **Destructive** (needs approval + retyped confirm) | Accent Peach Card `#fbe1d1` | **`#5d2a1a`** text, `#5d2a1a` 1px border | "DESTRUCTIVE — TYPE \"CONFIRM\" TO PROCEED" |
| **Success / approved / done** | Floating Product Artifact (white) | `#17191c` text | "Done" |
| **Denied / failed / error** | Floating Product Artifact (white) | `#5d2a1a` text | "Denied" / "Failed" |

This keeps the accent card genuinely rare (Steep's own "Do" rule — one per view maximum in the original
marketing-page context) while still giving External vs. Destructive a real visual distinction: External
uses the neutral ink-black ink on peach, Destructive uses the warmer, heavier sienna-brown ink+border on
the same peach surface — the "kraft paper" pairing the system describes for its accent cards, repurposed
here as an escalation signal instead of a decorative one.

## Confirmation prompt layout (replaces the old CLI-only mock)
```
+------------------------------------------------ Accent Peach Card, 24px radius --+
|  [EXTERNAL - APPROVAL NEEDED]              <- Tag/Category label, Sohne 14px      |
|                                                                                    |
|  Click 'Star' on github.com/org/repo        <- body 17px Sohne 400, #17191c       |
|  Account: Chrome profile "Work"             <- caption 15px, #777b86              |
|                                                                                    |
|  [screenshot thumbnail - Floating Artifact, white, 20px radius, subtle shadow]    |
|                                                                                    |
|  ( Approve - filled pill )   ( Deny - ghost pill )   ( Edit -> text link )        |
+------------------------------------------------------------------------------------+
```
Destructive steps use the same layout with the sienna-brown ink/border variant and an added inline input
styled as the Input/Composer component: `Type "CONFIRM" to proceed:`.

## Do's and Don'ts (Pixel-Agent-specific, in addition to the general Steep rules in the token files)
- **Do** keep the Accent Peach Card exclusively for risk-state attention (External/Destructive) in this
  product — don't also use it for generic marketing-style callouts, or it stops reading as "pay attention."
- **Do** always pair the peach card with its text label; never ship a version that relies on the ink-black
  vs. sienna-brown color difference alone to convey External vs. Destructive.
- **Do** use Floating Product Artifact styling for the live screenshot preview and any trace/log viewer —
  this is the system's designated slot for "product UI shown as evidence," which is exactly what a
  screenshot-in-a-confirmation-prompt is.
- **Don't** introduce new chromatic colors (no red/green/blue status dots) even for "success" vs. "error" —
  use ink-black vs. sienna-brown ink on the neutral/white surfaces instead, per the Risk-State Mapping.
- **Don't** apply shadow to Neutral or Accent Peach cards — only Floating Product Artifacts get elevation,
  per the token system's own rule.

## Full reference
For the complete component catalog (nav link, avatar bubble, tag, layout grid, imagery guidance, agent
prompt examples for generating new components), see `docs/design-tokens/DESIGN_source.md`. Any new GUI
component must be built from `docs/design-tokens/tokens.json` values, not new arbitrary ones.
