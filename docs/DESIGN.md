# Design System — Confirmation UI & Dashboard

Applies to `src/confirmation/prompt_ui.py` and any future dashboard/observability viewer. v1 ships as a
console/CLI UI; this system is written so it also works when a GUI/web dashboard is added later.

## Principles
- Confirmation prompts must be scannable in under 3 seconds — the user is interrupted mid-task, so clarity
  beats decoration.
- Risk level must be visually obvious before the user reads any text (color-coded).
- Never rely on color alone — pair every color cue with a text label (accessibility).

## Color scheme

| Purpose | Color | Hex | Usage |
|---|---|---|---|
| Local/reversible action (informational) | Slate blue | `#4A5EE8` | Log lines, non-blocking notices |
| External/irreversible action (needs approval) | Amber | `#E8A23C` | Confirmation prompt border/header |
| Destructive action (needs approval + re-type) | Red | `#D9453D` | Confirmation prompt border/header, re-type field |
| Success / approved / completed | Green | `#3CA86E` | Outcome logs, approval confirmation |
| Denied / failed | Muted red | `#B04A44` | Denied/failed outcome logs |
| Background (dashboard, if/when built) | Near-black | `#0F1115` | Base background |
| Background (panels) | Dark slate | `#181B22` | Card/panel background |
| Primary text | Off-white | `#E8E9ED` | Body text |
| Secondary text | Muted gray | `#8B8F9A` | Timestamps, metadata |

## Typography
- **UI/body font:** Inter (fallback: system-ui, sans-serif) — clean, highly legible at small sizes for
  dashboard/log text.
- **Monospace font:** JetBrains Mono (fallback: Consolas, monospace) — used for logged actions, selectors,
  file paths, and any raw data shown to the user (so it's visually distinct from prose).
- **Sizing:** body 14px, headers 18–22px, monospace log lines 13px. Console/CLI v1 has no font control, but
  these values apply the moment a GUI/dashboard is built.

## Confirmation prompt layout (console v1)
```
┌─ [AMBER] EXTERNAL ACTION — APPROVAL NEEDED ────────────────┐
│ Action: Click 'Star' on github.com/org/repo                │
│ Account/session: Chrome profile "Work"                     │
│ Screenshot: ./logs/task_042/step_07.png                    │
│                                                              │
│ [A]pprove   [D]eny   [E]dit and approve                     │
└──────────────────────────────────────────────────────────────┘
```
Destructive actions use the same layout in red, with an added line: `Type "CONFIRM" to proceed:`

## Future dashboard notes (Phase 5+)
When a GUI/web dashboard is added for trace replay (`trace_replay.py`), reuse this exact palette and
typography rather than introducing a new theme — keeps visual risk-cues consistent between the live
confirmation prompt and the historical log viewer.
