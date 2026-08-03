from unittest.mock import MagicMock, patch

from src.doctor import (
    CheckResult,
    check_config,
    check_desktop_control,
    check_encryption_at_rest,
    check_playwright_chromium,
    check_semantic_layer,
    check_tesseract,
    check_writable_dirs,
    run_diagnostics,
)


def test_check_config_passes_with_valid_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    result = check_config()
    assert result.passed
    assert "loaded OK" in result.detail


def test_check_config_fails_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = check_config()
    assert not result.passed
    assert "GEMINI_API_KEY" in result.detail


def test_check_tesseract_reports_missing_binary():
    with patch("pytesseract.get_tesseract_version", side_effect=FileNotFoundError("no such file")):
        result = check_tesseract()
    assert not result.passed
    assert result.optional is False
    assert "not found on PATH" in result.detail


def test_check_tesseract_reports_success():
    with patch("pytesseract.get_tesseract_version", return_value="5.3.4"):
        result = check_tesseract()
    assert result.passed
    assert "5.3.4" in result.detail
    assert "found on PATH" in result.detail


def test_check_tesseract_uses_explicit_tesseract_cmd_when_given():
    with patch("pytesseract.get_tesseract_version", return_value="5.3.4"):
        result = check_tesseract(tesseract_cmd=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    assert result.passed
    assert "TESSERACT_CMD=" in result.detail


def test_check_tesseract_reports_helpful_hint_when_explicit_cmd_is_wrong():
    with patch("pytesseract.get_tesseract_version", side_effect=FileNotFoundError("bad path")):
        result = check_tesseract(tesseract_cmd=r"C:\wrong\path\tesseract.exe")
    assert not result.passed
    assert "TESSERACT_CMD=" in result.detail
    assert "does not point at a working Tesseract binary" in result.detail


def test_check_playwright_chromium_reports_launch_failure():
    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.side_effect = RuntimeError(
            "Executable doesn't exist"
        )
        result = check_playwright_chromium()
    assert not result.passed
    assert "playwright install chromium" in result.detail


def test_check_playwright_chromium_reports_success():
    mock_browser = MagicMock()
    with patch("playwright.sync_api.sync_playwright") as mock_pw:
        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        result = check_playwright_chromium()
    assert result.passed
    mock_browser.close.assert_called_once()


def test_check_desktop_control_is_marked_optional_on_failure():
    """No real display available (e.g. this sandbox, or a headless CI
    runner) must be reported, but never as a blocking failure -- mirrors
    main.py's own web-only graceful degradation."""
    with patch.dict("sys.modules", {"pyautogui": None}):
        result = check_desktop_control()
    assert result.optional is True
    # optional=True regardless of pass/fail -- what matters is it never
    # blocks the exit code (see test_run_diagnostics_exit_code_* below).


def test_check_writable_dirs_reports_success(tmp_path):
    from dataclasses import dataclass

    @dataclass
    class _FakeCfg:
        profiles_dir = tmp_path / "profiles"
        log_dir = tmp_path / "logs"

    result = check_writable_dirs(_FakeCfg())
    assert result.passed


def test_check_semantic_layer_passes():
    result = check_semantic_layer()
    assert result.passed
    assert "SemanticRiskJudge" in result.detail


def test_check_encryption_at_rest_reports_unavailable_in_this_environment():
    """This build/test environment is Linux -- pywin32 genuinely isn't
    installed, so this should report unavailable (optional, never
    blocking) without any mocking at all."""
    result = check_encryption_at_rest()
    assert result.optional is True
    assert result.passed is False
    assert "pywin32" in result.detail


def test_run_diagnostics_returns_a_result_for_every_check(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    results = run_diagnostics(live=False)
    names = [r.name for r in results]
    assert "Config / GEMINI_API_KEY" in names
    assert "Tesseract OCR binary" in names
    assert "Playwright Chromium" in names
    assert "Desktop control (pyautogui + real display)" in names
    assert "Semantic risk layer (Phase 6)" in names
    assert "Encryption-at-rest (Windows DPAPI)" in names
    # --live not passed -- no real network call should have been attempted.
    assert "Gemini API (live call)" not in names


def test_run_diagnostics_skips_gemini_live_call_without_live_flag(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    with patch("src.brain.planner.HostedLLMPlanner") as mock_planner:
        run_diagnostics(live=False)
        mock_planner.assert_not_called()
