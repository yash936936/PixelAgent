"""
Loads the "Steep" design tokens from docs/design-tokens/tokens.json and turns
them into a Qt stylesheet (QSS) plus Python constants for anything that can't
be expressed in QSS (letter-spacing, font weights below what QFont supports
cleanly). This is the ONLY place colors/fonts/spacing/radius are allowed to
be hardcoded for the GUI — every widget imports from here rather than
embedding a hex value or px number itself. See docs/DESIGN.md.

If Signifier/Sohne aren't installed on the machine, Qt falls back to the
system-ui stack declared in docs/design-tokens/variables.css — this module
doesn't bundle or require the actual font files.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TOKENS_PATH = Path(__file__).resolve().parents[2] / "docs" / "design-tokens" / "tokens.json"


def _load_tokens() -> dict[str, Any]:
    with open(_TOKENS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_tokens = _load_tokens()


def _color(name: str) -> str:
    return _tokens["color"][name]["$value"]


# --- Colors (docs/DESIGN.md "Tokens — Colors") ---
INK_BLACK = _color("ink-black")
PAPER_WHITE = _color("paper-white")
MIST_GRAY = _color("mist-gray")
FOG_WHITE = _color("fog-white")
SLATE_GRAY = _color("slate-gray")
ASH_GRAY = _color("ash-gray")
SMOKE_GRAY = _color("smoke-gray")
BLUSH_PEACH = _color("blush-peach")
SIENNA_BROWN = _color("sienna-brown")

# --- Fonts ---
FONT_SIGNIFIER = _tokens["font"]["signifier"]["$value"]
FONT_SOHNE = _tokens["font"]["sohne"]["$value"]
# Fallback stack matches docs/design-tokens/variables.css exactly.
FONT_SANS_FALLBACK = f'"{FONT_SOHNE}", "Segoe UI", "Inter", sans-serif'
FONT_SERIF_FALLBACK = f'"{FONT_SIGNIFIER}", Georgia, serif'

# --- Spacing (px) --- keyed by int (e.g. SPACING[24] -> 24) for convenient use.
SPACING = {int(k): int(v["$value"].rstrip("px")) for k, v in _tokens["spacing"].items() if k != "unit"}

# --- Radius (px) ---
RADIUS_BUTTON = 9999
RADIUS_CARD = 24
RADIUS_INPUT = 16
RADIUS_ELEVATED = 20

# --- Risk-state mapping (docs/DESIGN.md "Risk-State Mapping") ---
RISK_STYLE = {
    "local": {"bg": MIST_GRAY, "ink": INK_BLACK, "border": "transparent", "label": "LOCAL — RUNNING AUTOMATICALLY"},
    "external": {"bg": BLUSH_PEACH, "ink": INK_BLACK, "border": INK_BLACK, "label": "EXTERNAL — APPROVAL NEEDED"},
    "destructive": {"bg": BLUSH_PEACH, "ink": SIENNA_BROWN, "border": SIENNA_BROWN, "label": 'DESTRUCTIVE — TYPE "CONFIRM" TO PROCEED'},
    "done": {"bg": PAPER_WHITE, "ink": INK_BLACK, "border": "transparent", "label": "DONE"},
    "denied": {"bg": PAPER_WHITE, "ink": SIENNA_BROWN, "border": "transparent", "label": "DENIED"},
    "error": {"bg": PAPER_WHITE, "ink": SIENNA_BROWN, "border": "transparent", "label": "FAILED"},
}


def build_stylesheet() -> str:
    """Global QSS applied at the QApplication level. Component-specific
    styling (risk-colored cards) is applied per-widget via RISK_STYLE above,
    since QSS alone can't express "one of three states chosen at runtime"
    cleanly without dynamic properties."""
    return f"""
    QWidget {{
        background-color: {PAPER_WHITE};
        color: {INK_BLACK};
        font-family: {FONT_SANS_FALLBACK};
        font-size: 15px;
    }}

    QMainWindow, #dashboardRoot {{
        background-color: {PAPER_WHITE};
    }}

    QLabel[role="heading"] {{
        font-family: {FONT_SERIF_FALLBACK};
        font-size: 26px;
        font-weight: 400;
        color: {INK_BLACK};
    }}

    QLabel[role="subheading"] {{
        font-size: 15px;
        color: {SLATE_GRAY};
    }}

    QLabel[role="caption"] {{
        font-size: 13px;
        color: {SLATE_GRAY};
    }}

    QLabel[role="tag"] {{
        font-size: 12px;
        color: {ASH_GRAY};
    }}

    /* Pill Button — Filled (primary actions) */
    QPushButton[variant="filled"] {{
        background-color: {INK_BLACK};
        color: {PAPER_WHITE};
        border: 1px solid {INK_BLACK};
        border-radius: {RADIUS_BUTTON}px;
        padding: 10px 20px;
        font-size: 15px;
    }}
    QPushButton[variant="filled"]:hover {{
        background-color: #2a2d32;
    }}
    QPushButton[variant="filled"]:disabled {{
        background-color: {SMOKE_GRAY};
        border-color: {SMOKE_GRAY};
    }}

    /* Pill Button — Ghost (secondary actions) */
    QPushButton[variant="ghost"] {{
        background-color: transparent;
        color: {INK_BLACK};
        border: 1px solid {INK_BLACK};
        border-radius: {RADIUS_BUTTON}px;
        padding: 10px 20px;
        font-size: 15px;
    }}
    QPushButton[variant="ghost"]:hover {{
        background-color: {FOG_WHITE};
    }}

    /* Neutral Card */
    QFrame[card="neutral"] {{
        background-color: {MIST_GRAY};
        border-radius: {RADIUS_CARD}px;
        border: none;
    }}

    /* Floating Product Artifact — only surface with elevation */
    QFrame[card="floating"] {{
        background-color: {PAPER_WHITE};
        border-radius: {RADIUS_ELEVATED}px;
        border: 1px solid rgba(4, 23, 43, 0.05);
    }}

    /* Input / Composer */
    QLineEdit[variant="composer"], QTextEdit[variant="composer"] {{
        background-color: {PAPER_WHITE};
        border: 1px solid #ececec;
        border-radius: {RADIUS_INPUT}px;
        padding: 12px 16px;
        font-size: 15px;
        color: {INK_BLACK};
    }}

    QListWidget, QTreeWidget {{
        background-color: transparent;
        border: none;
    }}

    QTabWidget::pane {{
        border: none;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {SLATE_GRAY};
        padding: 8px 16px;
        font-size: 15px;
    }}
    QTabBar::tab:selected {{
        color: {INK_BLACK};
        font-weight: 500;
        border-bottom: 2px solid {INK_BLACK};
    }}
    """


def risk_card_qss(risk_key: str) -> str:
    """Per-widget stylesheet for a card in a given risk state — used where
    the global stylesheet's static QSS can't express a runtime-chosen state.
    risk_key must be one of RISK_STYLE's keys."""
    style = RISK_STYLE.get(risk_key, RISK_STYLE["local"])
    border = f"1px solid {style['border']}" if style["border"] != "transparent" else "none"
    return (
        f"background-color: {style['bg']}; color: {style['ink']}; "
        f"border: {border}; border-radius: {RADIUS_CARD}px;"
    )
