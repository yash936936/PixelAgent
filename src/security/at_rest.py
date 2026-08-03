"""
Encryption-at-rest for local SQLite stores, using Windows DPAPI
(CryptProtectData/CryptUnprotectData) rather than a user-managed passphrase
or a separately-stored symmetric key. See docs/DECISIONS.md's 2026-08-02
Phase 8 design-decision entry for the full threat model and reasoning --
summarized: this ties encrypted data to the current Windows user account
and machine automatically, with no key file to manage, lose, or leak. It's
the same mechanism Windows itself uses for saved Wi-Fi passwords and
Chrome's saved-password store.

DPAPI is Windows-only (via pywin32's win32crypt). On any other platform --
including this project's Linux build/test environment -- encryption is
unavailable. This module detects that and degrades to plaintext with a
loud, one-time warning, matching the existing graceful-degradation pattern
used by MouseKeyboard/OCREngine elsewhere in this codebase. This is a real,
known gap on non-Windows setups, not a silent security regression: callers
can check `is_available()` and the warning names exactly what's missing.
"""
from __future__ import annotations

_warned_unavailable = False


def is_available() -> bool:
    """Whether real DPAPI encryption can actually be used on this machine.
    False on any non-Windows platform, or on Windows without pywin32
    installed."""
    try:
        import win32crypt  # noqa: F401

        return True
    except ImportError:
        return False


def _warn_once() -> None:
    global _warned_unavailable
    if not _warned_unavailable:
        print(
            "[warn] Windows DPAPI is unavailable on this system (pywin32 not installed, or not "
            "running on Windows) -- episodic/semantic memory will be stored UNENCRYPTED. This is "
            "expected in non-Windows dev/test environments; on a real Windows deployment, install "
            "pywin32 (`pip install pywin32`) to enable encryption-at-rest. See docs/DECISIONS.md's "
            "2026-08-02 Phase 8 entry for the full design decision."
        )
        _warned_unavailable = True


def protect(plaintext: str) -> str:
    """Encrypts a string for storage, returning a string safe to write into
    a TEXT column. Falls back to returning the plaintext unchanged (with a
    one-time warning) if DPAPI is unavailable -- this is a deliberate,
    visible degradation, not a silent one. Encrypted output is
    hex-encoded so it round-trips safely through SQLite TEXT columns and
    JSON without any binary-data handling."""
    if not is_available():
        _warn_once()
        return plaintext

    import win32crypt

    encrypted_bytes = win32crypt.CryptProtectData(plaintext.encode("utf-8"), None, None, None, None, 0)
    return encrypted_bytes.hex()


def unprotect(stored_value: str) -> str:
    """Inverse of protect(). If DPAPI is unavailable, assumes stored_value
    is plaintext (matching what protect() would have stored in that same
    unavailable state) and returns it unchanged. If DPAPI IS available but
    stored_value isn't validly hex-encoded encrypted data, assumes it's a
    plaintext row written before encryption was enabled (or written while
    DPAPI was unavailable) and returns it as-is -- this keeps existing,
    pre-Phase-8 databases readable rather than crashing on old rows."""
    if not is_available():
        return stored_value

    import win32crypt

    try:
        encrypted_bytes = bytes.fromhex(stored_value)
        decrypted = win32crypt.CryptUnprotectData(encrypted_bytes, None, None, None, 0)
        # CryptUnprotectData returns (description, data) -- we only ever
        # pass None for the description on encrypt, so index [1] is the
        # actual plaintext bytes.
        return decrypted[1].decode("utf-8")
    except Exception:  # noqa: BLE001 - not valid encrypted hex, or DPAPI rejected it
        return stored_value
