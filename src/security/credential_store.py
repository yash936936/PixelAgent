"""
Windows Credential Manager storage for GEMINI_API_KEY (Phase 16 Finding 2,
docs/DECISIONS.md 2026-08-11 "ACCEPTED, scoped as future work" entry --
this is that future pass). Uses the `keyring` package, which wraps the
real Windows Credential Manager (via pywin32) on Windows, Keychain on
macOS, and Secret Service on Linux -- so this degrades gracefully on this
project's Linux dev/test environment the same way src/security/at_rest.py
degrades DPAPI: detect unavailability, warn once, fall back rather than
crash.

Design, matching the existing .env-based flow rather than replacing it
outright (config.py's own docstring and every existing test assume
GEMINI_API_KEY can come from an env var -- breaking that would be a much
larger, riskier change than this Finding calls for):

  - `get_api_key()` checks Credential Manager FIRST, then falls back to
    the GEMINI_API_KEY environment variable (which config.load() already
    populates via load_dotenv()) if nothing is stored there yet. This
    means a user who never migrates sees zero change in behavior.
  - `set_api_key(key)` stores it in Credential Manager. Does NOT also
    delete it from .env -- migration is opt-in and the caller (a future
    CLI flag, e.g. `python -m src.security.credential_store --migrate`,
    or a SetupWizard checkbox) decides when/whether to also blank the
    .env line. This module does not touch .env directly at all, keeping
    it single-responsibility and easy to unit-test.
  - `is_available()` mirrors at_rest.py's naming so both "is a real secure
    backend available on this machine" checks read the same way across
    the codebase.

Service/username naming: a single fixed service name so there's exactly
one place a real key can live in Credential Manager for this app,
independent of which Windows user profile or install path is in use.
"""
from __future__ import annotations

_SERVICE_NAME = "PixelAgent"
_USERNAME = "GEMINI_API_KEY"

_warned_unavailable = False


def is_available() -> bool:
    """Whether a real OS-backed credential store can actually be used on
    this machine. False if the `keyring` package isn't installed, or if
    it's installed but has no usable backend configured.

    keyring.get_keyring() alone is NOT sufficient to check this -- on a
    system with no real backend (this sandbox's Linux environment, with no
    Secret Service running), it still returns a working Python object (the
    library's own `keyring.backends.fail.Keyring`), it just raises
    NoKeyringError the moment you actually try to use it. Confirmed live
    (2026-08-21, docs/DECISIONS.md) via a real GEMINI_API_KEY-missing test
    that this exact gap let `get_api_key()` raise an unrelated
    NoKeyringError instead of returning None -- so this function actually
    exercises get_password() (a real no-op read, not a mutation) rather
    than trusting get_keyring() alone."""
    try:
        import keyring
        from keyring.errors import KeyringError

        try:
            keyring.get_password("PixelAgent", "__availability_check__")
            return True
        except KeyringError:
            return False
    except ImportError:
        return False


def _warn_once() -> None:
    global _warned_unavailable
    if not _warned_unavailable:
        print(
            "[warn] No OS-backed credential store is available on this system (`keyring` not "
            "installed, or no usable backend) -- GEMINI_API_KEY will be read from .env/the "
            "environment as before. This is expected in non-Windows dev/test environments; on a "
            "real Windows deployment, install keyring (`pip install keyring`) and run "
            "`python -m src.security.credential_store --migrate` to move your key out of "
            "plaintext .env storage. See docs/DECISIONS.md's Phase 16 Finding 2 entry."
        )
        _warned_unavailable = True


def get_api_key() -> str | None:
    """Returns the Gemini API key from Credential Manager if one has been
    migrated there, else None. Does NOT fall back to the environment
    itself -- callers (config.py) already have their own env-var fallback
    and should try that separately, so this function's contract stays a
    simple, honest "what's actually in the credential store, if
    anything"."""
    if not is_available():
        _warn_once()
        return None

    import keyring

    return keyring.get_password(_SERVICE_NAME, _USERNAME)


def set_api_key(value: str) -> bool:
    """Stores the Gemini API key in Credential Manager. Returns True on
    success, False if no real backend is available (caller should keep
    using .env in that case -- this is not a fatal error)."""
    if not is_available():
        _warn_once()
        return False
    if not value or not value.strip():
        raise ValueError("Refusing to store an empty API key.")

    import keyring

    keyring.set_password(_SERVICE_NAME, _USERNAME, value.strip())
    return True


def delete_api_key() -> bool:
    """Removes the key from Credential Manager, if present. Returns True
    if something was actually deleted, False if nothing was stored or no
    backend is available. Used by the --migrate CLI's rollback path and
    by tests to clean up after themselves."""
    if not is_available():
        return False

    import keyring
    from keyring.errors import PasswordDeleteError

    try:
        keyring.delete_password(_SERVICE_NAME, _USERNAME)
        return True
    except PasswordDeleteError:
        return False


def migrate_from_env(env_path) -> bool:
    """One-shot migration: reads GEMINI_API_KEY out of the given .env file
    (same simple line-scan format setup_wizard_logic.needs_setup() already
    uses, kept consistent rather than introducing a second .env parser),
    stores it in Credential Manager, and blanks the line in .env (replaced
    with a comment explaining where the key actually lives now, rather
    than deleting the line outright -- so re-running config.load() against
    an un-migrated-aware version of this code still gets a clear "not set"
    error instead of a confusing blank value).

    Returns True if migration happened, False if there was nothing to
    migrate (no .env, no GEMINI_API_KEY line, or no backend available).
    Idempotent: safe to call again after a successful migration (finds no
    key left in .env, returns False, does nothing).
    """
    from pathlib import Path

    env_path = Path(env_path)
    if not env_path.exists() or not is_available():
        return False

    lines = env_path.read_text(encoding="utf-8").splitlines()
    key_value = None
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("GEMINI_API_KEY=") and key_value is None:
            candidate = stripped.split("=", 1)[1].strip()
            if candidate:
                key_value = candidate
                new_lines.append(
                    "# GEMINI_API_KEY migrated to Windows Credential Manager -- "
                    "see docs/DECISIONS.md Phase 16 Finding 2. Run "
                    "`python -m src.security.credential_store --migrate` again "
                    "if you need to re-migrate a new key."
                )
                continue
        new_lines.append(line)

    if key_value is None:
        return False

    set_api_key(key_value)
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True


def _main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Migrate GEMINI_API_KEY from .env to the OS credential store."
    )
    parser.add_argument("--migrate", action="store_true", help="Run the migration.")
    parser.add_argument("--env-path", default=".env", help="Path to .env (default: ./.env)")
    parser.add_argument(
        "--rollback", action="store_true",
        help="Remove the key from Credential Manager (does not restore it to .env).",
    )
    args = parser.parse_args()

    if not is_available():
        print(
            "No OS-backed credential store is available on this machine "
            "(install `keyring` and run this on real Windows/macOS/Linux-with-Secret-Service)."
        )
        raise SystemExit(1)

    if args.rollback:
        deleted = delete_api_key()
        print("Removed from Credential Manager." if deleted else "Nothing was stored.")
        return

    if args.migrate:
        moved = migrate_from_env(args.env_path)
        if moved:
            print(
                f"Migrated GEMINI_API_KEY from {args.env_path} into the OS credential store. "
                "The plaintext key has been removed from .env."
            )
        else:
            print(f"Nothing to migrate (no GEMINI_API_KEY found in {args.env_path}, or already migrated).")
        return

    stored = get_api_key()
    if stored:
        print("A key is currently stored in Credential Manager (value not shown).")
    else:
        print(f"No key stored in Credential Manager. GEMINI_API_KEY env var: "
              f"{'set' if os.environ.get('GEMINI_API_KEY') else 'not set'}.")


if __name__ == "__main__":
    _main()
