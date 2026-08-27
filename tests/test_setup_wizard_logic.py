from src.gui.setup_wizard_logic import (
    build_env_contents,
    looks_like_a_real_api_key,
    needs_setup,
    write_env_file,
)


def test_needs_setup_true_when_no_env_file(tmp_path):
    assert needs_setup(tmp_path / "does_not_exist.env") is True


def test_needs_setup_true_when_env_has_empty_api_key(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=\nDEFAULT_CHROME_PROFILE=Default\n")
    assert needs_setup(env_path) is True


def test_needs_setup_true_when_env_missing_api_key_line_entirely(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("DEFAULT_CHROME_PROFILE=Default\n")
    assert needs_setup(env_path) is True


def test_needs_setup_false_when_env_has_a_real_looking_key(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=AQ.FAKE_TEST_KEY_PREFIX_DO_NOT_USE\n")
    assert needs_setup(env_path) is False


def test_looks_like_a_real_api_key_rejects_blank():
    assert looks_like_a_real_api_key("") is False
    assert looks_like_a_real_api_key("   ") is False


def test_looks_like_a_real_api_key_rejects_placeholder_text():
    assert looks_like_a_real_api_key("your-api-key-here") is False


def test_looks_like_a_real_api_key_rejects_a_url():
    assert looks_like_a_real_api_key("https://aistudio.google.com/apikey") is False


def test_looks_like_a_real_api_key_rejects_too_short():
    assert looks_like_a_real_api_key("abc") is False


def test_looks_like_a_real_api_key_accepts_a_real_looking_key():
    assert looks_like_a_real_api_key("AQ.FAKE_TEST_KEY_DO_NOT_USE_1234567890abcdef") is True


def test_build_env_contents_includes_all_provided_fields():
    contents = build_env_contents("my-key", "Profile 3", r"C:\Users\me\Chrome")
    assert "GEMINI_API_KEY=my-key" in contents
    assert "DEFAULT_CHROME_PROFILE=Profile 3" in contents
    assert r"PROFILES_DIR=C:\Users\me\Chrome" in contents


def test_build_env_contents_defaults_chrome_profile_when_blank():
    contents = build_env_contents("my-key", "", "")
    assert "DEFAULT_CHROME_PROFILE=Default" in contents


def test_build_env_contents_omits_profiles_dir_when_blank():
    contents = build_env_contents("my-key", "Default", "")
    assert "PROFILES_DIR=" not in contents


def test_write_env_file_creates_a_loadable_file(tmp_path):
    env_path = tmp_path / ".env"
    write_env_file(env_path, "my-real-key", "Profile 3", "/some/path")
    assert env_path.exists()
    contents = env_path.read_text()
    assert "GEMINI_API_KEY=my-real-key" in contents
    assert needs_setup(env_path) is False


def test_write_env_file_overwrites_existing_file(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=old-key\n")
    write_env_file(env_path, "new-key")
    assert "new-key" in env_path.read_text()
    assert "old-key" not in env_path.read_text()


def test_build_env_contents_includes_llm_model_when_provided():
    contents = build_env_contents("my-key", "Default", "", "gemini-3.0-pro")
    assert "LLM_MODEL=gemini-3.0-pro" in contents


def test_build_env_contents_omits_llm_model_when_blank():
    contents = build_env_contents("my-key", "Default", "", "")
    assert "LLM_MODEL=" not in contents


def test_write_env_file_persists_llm_model(tmp_path):
    env_path = tmp_path / ".env"
    write_env_file(env_path, "my-real-key", "Profile 3", "/some/path", "gemini-3.0-pro")
    assert "LLM_MODEL=gemini-3.0-pro" in env_path.read_text(encoding="utf-8")
