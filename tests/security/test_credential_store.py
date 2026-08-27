"""
Tests for src/security/credential_store.py (Phase 16 Finding 2 migration).

Uses keyring's own in-memory test backend (keyrings.alt / keyring's
built-in `keyring.backends.fail.Keyring` for the unavailable path, and a
plain dict-backed fake for the available path) rather than the real
Windows Credential Manager, which doesn't exist in this Linux test
environment -- same reasoning as src/security/at_rest.py's own tests
(see tests/security/test_at_rest.py if present) for why a fake backend is
the right tool here, not a skip.
"""
from __future__ import annotations

import keyring
import pytest

from src.security import credential_store


class _FakeKeyring:
    """Minimal in-memory keyring backend so tests can exercise the
    "a real backend IS available" path deterministically, without
    depending on this machine having Secret Service/Keychain/Credential
    Manager actually configured.

    Deliberately does NOT subclass keyring.backend.KeyringBackend.
    Confirmed live (2026-08-26): merely DEFINING a KeyringBackend
    subclass at module import time registers it in keyring's own global
    backend-discovery registry (via KeyringBackend.__subclasses__()) --
    with priority=1 outranking the real fail.Keyring's priority=0, so
    keyring.get_password() would silently start resolving to a fresh,
    unrelated instance of this class (not the one this fixture actually
    populates) for the rest of the test session, independent of whether
    a test monkeypatches anything. That made
    TestAvailability.test_unavailable_when_no_real_backend fail with
    "assert True is False" even when run in isolation, since is_available()
    saw a real (if empty) backend instead of the intended no-backend
    condition. This class only needs to be duck-typed to match what the
    fixture's monkeypatches call directly -- it never needs to go through
    keyring's own backend-selection machinery at all."""

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self._store.get((service, username))

    def set_password(self, service, username, password):
        self._store[(service, username)] = password

    def delete_password(self, service, username):
        key = (service, username)
        if key not in self._store:
            from keyring.errors import PasswordDeleteError

            raise PasswordDeleteError("not found")
        del self._store[key]


@pytest.fixture
def fake_backend(monkeypatch):
    backend = _FakeKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    return backend


class TestAvailability:
    def test_unavailable_when_backend_raises_no_keyring_error(self, monkeypatch):
        """Deliberately forces the no-backend condition rather than relying
        on the ambient environment having no real backend -- this Linux
        sandbox genuinely has no working keyring backend
        (keyring.backends.fail.Keyring), but a real Windows machine has a
        real Credential Manager backend and correctly reports
        is_available()==True there (confirmed live, 2026-08-26: this test
        as originally written -- asserting False with no monkeypatch --
        failed on Windows for exactly this reason, which is Windows
        working correctly, not a bug). Forcing the failure directly makes
        this test's outcome the same on every machine."""
        from keyring.errors import NoKeyringError

        def _raise(*a, **kw):
            raise NoKeyringError("no backend")

        monkeypatch.setattr(keyring, "get_password", _raise)
        assert credential_store.is_available() is False

    def test_available_with_fake_backend(self, fake_backend):
        assert credential_store.is_available() is True


class TestGetSetDeleteApiKey:
    def test_get_returns_none_when_nothing_stored(self, fake_backend):
        assert credential_store.get_api_key() is None

    def test_set_then_get_roundtrips(self, fake_backend):
        credential_store.set_api_key("real-looking-key-123")
        assert credential_store.get_api_key() == "real-looking-key-123"

    def test_set_strips_whitespace(self, fake_backend):
        credential_store.set_api_key("  key-with-space  ")
        assert credential_store.get_api_key() == "key-with-space"

    def test_set_rejects_empty_value(self, fake_backend):
        with pytest.raises(ValueError):
            credential_store.set_api_key("   ")

    def test_get_returns_none_when_backend_unavailable(self, monkeypatch):
        monkeypatch.setattr(credential_store, "is_available", lambda: False)
        assert credential_store.get_api_key() is None

    def test_set_returns_false_when_backend_unavailable(self, monkeypatch):
        monkeypatch.setattr(credential_store, "is_available", lambda: False)
        assert credential_store.set_api_key("some-key") is False

    def test_delete_removes_stored_key(self, fake_backend):
        credential_store.set_api_key("to-be-deleted")
        assert credential_store.delete_api_key() is True
        assert credential_store.get_api_key() is None

    def test_delete_returns_false_when_nothing_stored(self, fake_backend):
        assert credential_store.delete_api_key() is False

    def test_delete_returns_false_when_backend_unavailable(self, monkeypatch):
        monkeypatch.setattr(credential_store, "is_available", lambda: False)
        assert credential_store.delete_api_key() is False


class TestMigrateFromEnv:
    def test_migrates_key_out_of_env_file(self, tmp_path, fake_backend):
        env_path = tmp_path / ".env"
        env_path.write_text("GEMINI_API_KEY=my-real-key\nDEFAULT_CHROME_PROFILE=Default\n")  # pragma: allowlist secret

        moved = credential_store.migrate_from_env(env_path)

        assert moved is True
        assert credential_store.get_api_key() == "my-real-key"
        contents = env_path.read_text()
        assert "my-real-key" not in contents
        assert "DEFAULT_CHROME_PROFILE=Default" in contents  # untouched
        assert "migrated to Windows Credential Manager" in contents

    def test_idempotent_second_call_does_nothing(self, tmp_path, fake_backend):
        env_path = tmp_path / ".env"
        env_path.write_text("GEMINI_API_KEY=my-real-key\n")

        credential_store.migrate_from_env(env_path)
        second_call = credential_store.migrate_from_env(env_path)

        assert second_call is False

    def test_returns_false_when_no_env_file(self, tmp_path, fake_backend):
        assert credential_store.migrate_from_env(tmp_path / "nonexistent.env") is False

    def test_returns_false_when_no_api_key_line(self, tmp_path, fake_backend):
        env_path = tmp_path / ".env"
        env_path.write_text("DEFAULT_CHROME_PROFILE=Default\n")
        assert credential_store.migrate_from_env(env_path) is False

    def test_returns_false_when_backend_unavailable(self, tmp_path, monkeypatch):
        env_path = tmp_path / ".env"
        env_path.write_text("GEMINI_API_KEY=my-real-key\n")
        monkeypatch.setattr(credential_store, "is_available", lambda: False)

        assert credential_store.migrate_from_env(env_path) is False
        # .env must be left completely untouched when migration can't happen
        assert "GEMINI_API_KEY=my-real-key" in env_path.read_text()


class TestConfigLoadFallsBackToCredentialStore:
    def test_config_load_uses_credential_store_when_env_var_missing(self, tmp_path, monkeypatch, fake_backend):
        """The actual integration point: config.load() must fall back to
        the credential store, not just fail, when GEMINI_API_KEY isn't in
        the environment/.env at all."""
        import src.config as config_module

        credential_store.set_api_key("key-from-credential-manager")
        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        cfg = config_module.load(env_path=str(tmp_path / "nonexistent.env"))

        assert cfg.gemini_api_key == "key-from-credential-manager"  # pragma: allowlist secret

    def test_config_load_still_fails_clearly_when_neither_source_has_a_key(self, tmp_path, monkeypatch):
        import src.config as config_module

        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(credential_store, "get_api_key", lambda: None)

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            config_module.load(env_path=str(tmp_path / "nonexistent.env"))

    def test_config_load_prefers_env_var_over_credential_store(self, tmp_path, monkeypatch, fake_backend):
        """Env var should win if both are somehow set -- least-surprise:
        an explicit .env/shell export is a more deliberate, visible choice
        than whatever's sitting in Credential Manager."""
        import src.config as config_module

        credential_store.set_api_key("key-from-credential-manager")
        monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)
        monkeypatch.setenv("GEMINI_API_KEY", "key-from-env")

        cfg = config_module.load(env_path=str(tmp_path / "nonexistent.env"))

        assert cfg.gemini_api_key == "key-from-env"  # pragma: allowlist secret
