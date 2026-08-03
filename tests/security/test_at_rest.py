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
    """This build/test environment is Linux -- pywin32 genuinely isn't
    installed, so this should be false without any mocking at all."""
    assert at_rest.is_available() is False


def test_protect_falls_back_to_plaintext_when_unavailable(capsys):
    """Real degradation path exercised for real in this environment (no
    mocking needed) -- pywin32 isn't installed here."""
    result = at_rest.protect("sensitive task instruction")
    assert result == "sensitive task instruction"
    captured = capsys.readouterr()
    assert "DPAPI is unavailable" in captured.out


def test_protect_warns_only_once(capsys):
    at_rest.protect("first")
    at_rest.protect("second")
    captured = capsys.readouterr()
    assert captured.out.count("DPAPI is unavailable") == 1


def test_unprotect_falls_back_to_returning_input_when_unavailable():
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
