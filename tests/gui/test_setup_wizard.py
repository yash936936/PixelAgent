from src.gui.widgets.setup_wizard import SetupWizard


def test_start_button_disabled_initially(qapp, tmp_path):
    wizard = SetupWizard(env_path=tmp_path / ".env")
    assert wizard._start_button.isEnabled() is False


def test_start_button_disabled_with_key_but_no_consent(qapp, tmp_path):
    wizard = SetupWizard(env_path=tmp_path / ".env")
    wizard._api_key_input.setText("AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE__4djIX1")
    assert wizard._start_button.isEnabled() is False


def test_start_button_disabled_with_consent_but_no_key(qapp, tmp_path):
    wizard = SetupWizard(env_path=tmp_path / ".env")
    wizard._consent_checkbox.setChecked(True)
    assert wizard._start_button.isEnabled() is False


def test_start_button_enabled_with_valid_key_and_consent(qapp, tmp_path):
    wizard = SetupWizard(env_path=tmp_path / ".env")
    wizard._api_key_input.setText("AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE__4djIX1")
    wizard._consent_checkbox.setChecked(True)
    assert wizard._start_button.isEnabled() is True


def test_start_button_disabled_for_placeholder_looking_key(qapp, tmp_path):
    wizard = SetupWizard(env_path=tmp_path / ".env")
    wizard._api_key_input.setText("your-api-key-here")
    wizard._consent_checkbox.setChecked(True)
    assert wizard._start_button.isEnabled() is False


def test_on_start_writes_env_file_and_accepts(qapp, tmp_path):
    env_path = tmp_path / ".env"
    wizard = SetupWizard(env_path=env_path)
    wizard._api_key_input.setText("AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE__4djIX1")
    wizard._profile_input.setText("Profile 3")
    wizard._consent_checkbox.setChecked(True)

    wizard._on_start()

    assert env_path.exists()
    contents = env_path.read_text()
    assert "GEMINI_API_KEY=AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE__4djIX1" in contents
    assert "DEFAULT_CHROME_PROFILE=Profile 3" in contents


def test_on_start_defaults_chrome_profile_when_left_blank(qapp, tmp_path):
    env_path = tmp_path / ".env"
    wizard = SetupWizard(env_path=env_path)
    wizard._api_key_input.setText("AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE__4djIX1")
    wizard._consent_checkbox.setChecked(True)

    wizard._on_start()

    assert "DEFAULT_CHROME_PROFILE=Default" in env_path.read_text()


def test_on_start_does_not_write_env_for_invalid_key(qapp, tmp_path, monkeypatch):
    """Defense in depth: even if the Get Started button were somehow
    triggered with an invalid key (e.g. a future UI bug bypassing the
    enabled-state check), _on_start() itself must still refuse to write
    a bad .env file."""
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    env_path = tmp_path / ".env"
    wizard = SetupWizard(env_path=env_path)
    wizard._api_key_input.setText("bad")
    wizard._consent_checkbox.setChecked(True)

    wizard._on_start()

    assert not env_path.exists()
