from unittest.mock import MagicMock, patch

import pytest

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


@pytest.fixture(autouse=True)
def _restore_pytesseract_tesseract_cmd():
    """Real test-isolation bug found live on Windows (2026-08-17,
    docs/DECISIONS.md): check_tesseract(tesseract_cmd=...) (src/doctor.py)
    sets `pytesseract.pytesseract.tesseract_cmd` -- a module-level global in
    the third-party pytesseract library itself, not something scoped to
    this test file -- and nothing here ever restored it afterward. A test
    below that deliberately passes a wrong path
    (test_check_tesseract_reports_helpful_hint_when_explicit_cmd_is_wrong)
    left that wrong path sitting in pytesseract's global state for the rest
    of the pytest session, which then silently broke
    tests/perception/test_ocr_solid_background_regression.py's real-Tesseract
    tests if they happened to run afterward in the same process -- a classic
    test-pollution bug, invisible when this file is run alone (as it was
    when originally written) and only surfacing once the full suite ran
    together. Fixed with this autouse fixture: snapshot the real value
    before each test in this file, restore it after, regardless of what any
    individual test mutates it to."""
    import pytesseract

    original = pytesseract.pytesseract.tesseract_cmd
    yield
    pytesseract.pytesseract.tesseract_cmd = original


def test_check_config_passes_with_valid_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("PROFILES_DIR", str(tmp_path / "profiles"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    result = check_config()
    assert result.passed
    assert "loaded OK" in result.detail


def test_check_config_fails_without_api_key(monkeypatch):
    """Real bug found live on Windows (2026-08-17, docs/DECISIONS.md):
    monkeypatch.delenv() alone only removes GEMINI_API_KEY from os.environ
    at the moment this test runs -- but config.load() calls load_dotenv()
    internally, which RE-reads a real .env file from disk (searching the
    current/parent directories) and re-populates os.environ from it. On
    this project's own Linux CI there's typically no real .env file
    present, so the original version of this test happened to work there;
    on the user's real Windows dev machine, a real .env with a real
    GEMINI_API_KEY exists (as it must, for the agent to function at all),
    so load_dotenv() silently undid the delenv() before check_config() ever
    ran, and the test's "fails without API key" scenario could never
    actually be constructed. Fixed by also patching load_dotenv itself to a
    no-op for this test, so the deleted env var stays deleted regardless of
    what real .env file exists on the machine running this suite.

    Second real bug found live on Windows (2026-08-26, docs/DECISIONS.md):
    once config.load() gained a Windows Credential Manager fallback (Phase
    16 Finding 2), this test failed again the same way -- "assert not
    True" -- because a real Windows machine's real Credential Manager is a
    THIRD possible source of a real key (env var, .env file, now Credential
    Manager) that this test wasn't blocking. Deleting the env var and
    stubbing load_dotenv was sufficient to simulate "no key anywhere" before
    that fallback existed; it no longer is on its own. Fixed by also
    patching credential_store.get_api_key() to None, so this test's actual
    intent -- no key available from ANY source -- holds regardless of what's
    actually stored on the machine running the suite."""
    import src.config as config_module
    import src.security.credential_store as credential_store_module

    monkeypatch.setattr(config_module, "load_dotenv", lambda *a, **kw: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(credential_store_module, "get_api_key", lambda: None)
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


def test_check_encryption_at_rest_reports_unavailable_when_pywin32_missing(monkeypatch):
    """Real bug found live on Windows (2026-08-17, docs/DECISIONS.md): the
    original version of this test asserted "unavailable" on the bare claim
    that pywin32 isn't installed in this environment -- true on this
    project's Linux CI, false on the real Windows machine this project
    targets, where pywin32 is genuinely installed (Phase 8's whole point)
    and encryption is correctly reported as available. That was correct
    behavior being flagged as a failure. Fixed the same way as
    tests/security/test_at_rest.py's equivalent fix: force the "pywin32 not
    installed" condition deterministically via sys.modules rather than
    relying on ambient environment truth, so this test checks the same real
    code path on every platform."""
    import sys

    monkeypatch.setitem(sys.modules, "win32crypt", None)
    result = check_encryption_at_rest()
    assert result.optional is True
    assert result.passed is False
    assert "pywin32" in result.detail


def test_check_encryption_at_rest_reports_available_when_pywin32_present(monkeypatch):
    """The counterpart to the test above -- added 2026-08-17 alongside the
    fix, since the "available" path (the actual real-Windows outcome this
    project cares about) had no test of its own before this."""
    import sys
    from unittest.mock import MagicMock

    monkeypatch.setitem(sys.modules, "win32crypt", MagicMock())
    result = check_encryption_at_rest()
    assert result.optional is True
    assert result.passed is True
    assert "encrypted" in result.detail


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
