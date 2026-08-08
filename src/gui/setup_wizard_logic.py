"""
Pure logic backing the first-run setup wizard (Phase 11, docs/DECISIONS.md
2026-08-02). Deliberately has NO PySide6/Qt import at all, so it can be
fully unit-tested without a display or even PySide6 installed -- the same
separation this project already uses for GateBridge/prompt_fn (business
logic testable independent of the UI framework it's wrapped in).

Fix for a real gap: src/gui/app.py previously called config.load() before
even constructing QApplication, so a fresh install with no .env file
crashed with a raw RuntimeError traceback before any window ever appeared
-- exactly the opposite of Phase 11's "someone who isn't the author can
download one file, install it, and get to a working first task with no
terminal/source access" success criterion. This module is what makes that
possible: detect the missing-setup case, collect what's needed through a
real dialog (see setup_wizard.py), and write a working .env file.
"""
from __future__ import annotations

from pathlib import Path


def needs_setup(env_path: Path) -> bool:
    """Whether the first-run wizard should show. True if no .env file
    exists at all, OR one exists but has no non-empty GEMINI_API_KEY line
    -- covers both a genuinely fresh install and a .env.example accidentally
    copied to .env without ever being filled in."""
    if not env_path.exists():
        return True

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("GEMINI_API_KEY="):
            value = stripped.split("=", 1)[1].strip()
            if value:
                return False
    return True


def looks_like_a_real_api_key(value: str) -> bool:
    """Cheap, deliberately permissive sanity check -- this is NOT
    validating the key actually works (that needs a real network call,
    which src/doctor.py's --live flag already does separately). This only
    catches the most common first-run mistakes: leaving the field blank,
    pasting a URL instead of a key, or pasting the literal placeholder
    text from .env.example."""
    value = value.strip()
    if not value:
        return False
    if value in ("your-api-key-here", "AQ....", "YOUR_API_KEY"):
        return False
    if " " in value or "http" in value.lower():
        return False
    return len(value) >= 10


def build_env_contents(
    gemini_api_key: str,
    default_chrome_profile: str = "Default",
    profiles_dir: str = "",
) -> str:
    """Builds a minimal, valid .env file's contents from wizard input.
    Deliberately minimal -- only the fields the wizard actually collects.
    Every other setting (rate limits, retention, etc.) keeps config.py's
    own sensible defaults rather than the wizard forcing an opinion on
    settings a first-run user has no way to make an informed choice
    about yet."""
    lines = [
        f"GEMINI_API_KEY={gemini_api_key.strip()}",
        f"DEFAULT_CHROME_PROFILE={default_chrome_profile.strip() or 'Default'}",
    ]
    if profiles_dir.strip():
        lines.append(f"PROFILES_DIR={profiles_dir.strip()}")
    lines.append("")  # trailing newline
    return "\n".join(lines)


def write_env_file(
    env_path: Path,
    gemini_api_key: str,
    default_chrome_profile: str = "Default",
    profiles_dir: str = "",
) -> None:
    """Writes a fresh .env file. Overwrites any existing file at env_path
    outright -- this is only ever called from the wizard after
    needs_setup() already confirmed there's nothing usable there to
    preserve, so there's no partial-merge logic to get wrong."""
    env_path.write_text(
        build_env_contents(gemini_api_key, default_chrome_profile, profiles_dir),
        encoding="utf-8",
    )
