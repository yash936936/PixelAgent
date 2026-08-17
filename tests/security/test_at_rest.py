import sys
from unittest.mock import MagicMock

import pytest

from src.security import at_rest


@pytest.fixture(autouse=True)
def _reset_warned_once_flag():
    """at_rest._warned_unavailable is a module-level flag so the warning
    only prints once per process -- reset it between tests so each test
    starts from a known state rather than being order-dependent on
    whether an earlier test already triggered it."""
    at_rest._warned_unavailable = False
    yield
    at_rest._warned_unavailable = False


def test_is_available_false_when_pywin32_not_installed(monkeypatch):
    """Forces the "pywin32 not installed" path deterministically rather
    than assuming ambient environment truth. Real bug found live
    (2026-08-17, docs/DECISIONS.md): this test originally asserted
    `is_available() is False` on the bare claim that "this environment is
    Linux, pywin32 genuinely isn't installed" -- true in this project's own
    Linux CI, but false the moment this suite actually ran on the real
    Windows machine it's meant to support, where pywin32 IS installed (by
    design -- see docs/PHASES.md Phase 8) and is_available() correctly
    returns True. That was correct behavior being flagged as a test
    failure, not a real bug. Fixed to force the "not installed" condition
    via sys.modules (setting the entry to None makes `import win32crypt`
    raise ImportError, the standard technique for this), so this test
    verifies the same real code path -- is_available()'s except ImportError
    branch -- on every platform, deterministically, rather than depending
    on what happens to be installed on whatever machine runs it."""
    monkeypatch.setitem(sys.modules, "win32crypt", None)
    assert at_rest.is_available() is False


def test_protect_falls_back_to_plaintext_when_unavailable(monkeypatch, capsys):
    """Forces the unavailable path the same way as the test above --
    real bug found live (2026-08-17): the original version relied on
    pywin32 genuinely being absent, which doesn't hold on the real Windows
    machine this project targets."""
    monkeypatch.setitem(sys.modules, "win32crypt", None)
    result = at_rest.protect("sensitive task instruction")
    assert result == "sensitive task instruction"
    captured = capsys.readouterr()
    assert "DPAPI is unavailable" in captured.out


def test_protect_warns_only_once(monkeypatch, capsys):
    """Same fix as the two tests above -- forces the unavailable path
    deterministically instead of assuming pywin32 is absent."""
    monkeypatch.setitem(sys.modules, "win32crypt", None)
    at_rest.protect("first")
    at_rest.protect("second")
    captured = capsys.readouterr()
    assert captured.out.count("DPAPI is unavailable") == 1


def test_unprotect_falls_back_to_returning_input_when_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "win32crypt", None)
    assert at_rest.unprotect("some stored value") == "some stored value"


def _install_fake_win32crypt(monkeypatch):
    """Simulates a real Windows DPAPI round-trip using a reversible fake
    (not real DPAPI, which isn't installable in this Linux environment) --
    CryptProtectData/CryptUnprotectData's actual signatures are mimicked
    closely enough to exercise protect()/unprotect()'s own logic (hex
    encoding, the (description, data) tuple unpacking) rather than trusting
    a black box."""
    fake_module = MagicMock()

    def fake_protect(data_bytes, *args):
        # A trivial reversible "encryption" for test purposes: reverse the
        # bytes. Real DPAPI is opaque; this just needs to be invertible.
        return data_bytes[::-1]

    def fake_unprotect(data_bytes, *args):
        return (None, data_bytes[::-1])

    fake_module.CryptProtectData.side_effect = fake_protect
    fake_module.CryptUnprotectData.side_effect = fake_unprotect
    monkeypatch.setitem(sys.modules, "win32crypt", fake_module)
    return fake_module


def test_protect_and_unprotect_round_trip_when_available(monkeypatch):
    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(at_rest, "is_available", lambda: True)

    encrypted = at_rest.protect("sensitive task instruction")
    assert encrypted != "sensitive task instruction"  # actually transformed
    assert at_rest.unprotect(encrypted) == "sensitive task instruction"


def test_protect_output_is_valid_hex_when_available(monkeypatch):
    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(at_rest, "is_available", lambda: True)

    encrypted = at_rest.protect("hello")
    bytes.fromhex(encrypted)  # must not raise


def test_unprotect_returns_input_unchanged_for_pre_encryption_plaintext_rows(monkeypatch):
    """A database row written before encryption was enabled (or while
    DPAPI was unavailable) is plain text, not valid hex-encoded encrypted
    data. unprotect() must return it as-is rather than crash, so existing
    pre-Phase-8 databases stay readable."""
    _install_fake_win32crypt(monkeypatch)
    monkeypatch.setattr(at_rest, "is_available", lambda: True)

    assert at_rest.unprotect("this is not hex-encoded ciphertext at all") == (
        "this is not hex-encoded ciphertext at all"
    )
