from unittest.mock import MagicMock, patch

from src.gui import app as app_module
from src.gui.widgets.setup_wizard import SetupWizard


def test_main_skips_wizard_when_env_already_set_up(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=AQ.realkey123\n")

    fake_app = MagicMock()
    fake_app.exec.return_value = 0
    with patch.object(app_module, "MainWindow") as mock_window_cls, \
         patch.object(SetupWizard, "exec") as mock_wizard_exec, \
         patch.object(app_module, "QApplication", return_value=fake_app):
        result = app_module.main()

    mock_wizard_exec.assert_not_called()
    mock_window_cls.assert_called_once()
    assert result == 0


def test_main_shows_wizard_when_no_env_exists(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    fake_app = MagicMock()
    fake_app.exec.return_value = 0
    with patch.object(SetupWizard, "exec", return_value=SetupWizard.DialogCode.Rejected) as mock_wizard_exec, \
         patch.object(app_module, "MainWindow") as mock_window_cls, \
         patch.object(app_module, "QApplication", return_value=fake_app):
        result = app_module.main()

    mock_wizard_exec.assert_called_once()
    # Wizard was cancelled -- must exit cleanly without ever reaching
    # config.load()/MainWindow, which would just raise the same
    # unhelpful RuntimeError this wizard exists to prevent.
    mock_window_cls.assert_not_called()
    assert result == 0


def test_main_proceeds_to_config_and_window_after_wizard_accepted(qapp, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env_path = tmp_path / ".env"

    def fake_accept(self):
        # Simulate what a real completed wizard does: write a usable .env.
        env_path.write_text("GEMINI_API_KEY=AQ.realkey123\n")
        return SetupWizard.DialogCode.Accepted

    fake_app = MagicMock()
    fake_app.exec.return_value = 0
    with patch.object(SetupWizard, "exec", fake_accept), \
         patch.object(app_module, "MainWindow") as mock_window_cls, \
         patch.object(app_module, "QApplication", return_value=fake_app):
        result = app_module.main()

    mock_window_cls.assert_called_once()
    assert result == 0
