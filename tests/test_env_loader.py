"""T33：多 LLM 环境配置文件加载测试。"""

import os

import pytest

from packages.music_core.config.env_loader import (
    load_env,
    mask_env_value,
    mask_value,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """每个测试后恢复 os.environ；测试前移除 profile 相关变量，避免 conftest 的 LLM_PROVIDER 干扰。"""
    saved = dict(os.environ)
    for key in ("LLM_PROVIDER", "LLM_ENV_PROFILE", "LLM_ENV_FILE"):
        os.environ.pop(key, None)
    yield
    os.environ.clear()
    os.environ.update(saved)


def _write(tmp_path, name: str, content: str):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_no_profile_loads_env(tmp_path):
    _write(tmp_path, ".env", "FOO=bar\nLLM_PROVIDER=mock\n")
    info = load_env(env_dir=tmp_path)
    assert os.environ["FOO"] == "bar"
    assert os.environ["LLM_PROVIDER"] == "mock"
    assert any(p.name == ".env" for p in info.loaded_files)


def test_profile_mock_maps_to_mock_env(tmp_path):
    _write(tmp_path, ".env", "LLM_PROVIDER=mock\n")
    _write(tmp_path, ".mock.env", "LLM_PROVIDER=mock\nAUDIO_RENDERER=fallback\n")
    info = load_env(profile="mock", env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "mock"
    assert os.environ["AUDIO_RENDERER"] == "fallback"
    assert any(p.name == ".mock.env" for p in info.loaded_files)


def test_env_profile_var_selects_lmstudio(tmp_path, monkeypatch):
    _write(tmp_path, ".env", "LLM_PROVIDER=mock\n")
    _write(tmp_path, ".lmstudio.env", "LLM_PROVIDER=lmstudio\nLMSTUDIO_MODEL=local\n")
    monkeypatch.setenv("LLM_ENV_PROFILE", "lmstudio")
    info = load_env(env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "lmstudio"
    assert os.environ["LMSTUDIO_MODEL"] == "local"
    assert info.profile == "lmstudio"


def test_env_profile_var_selects_deepseek(tmp_path, monkeypatch):
    _write(tmp_path, ".deepseek.env", "LLM_PROVIDER=deepseek\nDEEPSEEK_API_KEY=sk-test\n")
    monkeypatch.setenv("LLM_ENV_PROFILE", "deepseek")
    info = load_env(env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "deepseek"
    assert info.profile == "deepseek"


def test_env_profile_var_selects_gemini(tmp_path, monkeypatch):
    _write(tmp_path, ".gemini.env", "LLM_PROVIDER=gemini\nGEMINI_API_KEY=sk-test\nGEMINI_MODEL=gemini-3.5-flash\n")
    monkeypatch.setenv("LLM_ENV_PROFILE", "gemini")
    info = load_env(env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "gemini"
    assert os.environ["GEMINI_MODEL"] == "gemini-3.5-flash"
    assert info.profile == "gemini"


def test_gemini_env_missing_no_crash(tmp_path):
    info = load_env(profile="gemini", env_dir=tmp_path)  # 无 .gemini.env
    assert any(p.name == ".gemini.env" for p in info.missing_files)


def test_env_file_overrides_profile(tmp_path, monkeypatch):
    _write(tmp_path, ".env", "LLM_PROVIDER=mock\n")
    _write(tmp_path, ".mock.env", "LLM_PROVIDER=mock\n")
    _write(tmp_path, ".custom.env", "LLM_PROVIDER=lmstudio\n")
    info = load_env(profile="mock", env_file=".custom.env", env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "lmstudio"
    assert any(p.name == ".custom.env" for p in info.loaded_files)
    assert info.explicit_env_file == ".custom.env"


def test_env_file_var_overrides_profile(tmp_path, monkeypatch):
    _write(tmp_path, ".mock.env", "LLM_PROVIDER=mock\n")
    _write(tmp_path, ".custom.env", "LLM_PROVIDER=deepseek\nDEEPSEEK_API_KEY=sk-file\n")
    monkeypatch.setenv("LLM_ENV_PROFILE", "mock")
    monkeypatch.setenv("LLM_ENV_FILE", str(tmp_path / ".custom.env"))
    info = load_env(env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "deepseek"


def test_system_env_highest_priority(tmp_path, monkeypatch):
    _write(tmp_path, ".env", "LLM_PROVIDER=deepseek\n")
    _write(tmp_path, ".mock.env", "LLM_PROVIDER=mock\n")
    monkeypatch.setenv("LLM_PROVIDER", "lmstudio")  # 系统环境变量
    load_env(profile="mock", env_dir=tmp_path)
    assert os.environ["LLM_PROVIDER"] == "lmstudio"


def test_missing_env_file_no_crash(tmp_path):
    info = load_env(profile="mock", env_dir=tmp_path)  # 无 .env 也无 .mock.env
    assert any(p.name == ".mock.env" for p in info.missing_files)
    # 不崩溃且不会误设置
    assert "LLM_PROVIDER" not in os.environ or os.environ["LLM_PROVIDER"]


def test_missing_dotenv_no_crash(tmp_path):
    info = load_env(env_dir=tmp_path)  # 目录里什么都没有
    assert not info.loaded_files
    assert not info.missing_files


def test_unknown_profile_raises(tmp_path):
    with pytest.raises(ValueError, match="未知的 LLM_ENV_PROFILE"):
        load_env(profile="no_such_profile", env_dir=tmp_path)


def test_mask_value():
    assert mask_value(None) == "<unset>"
    assert mask_value("") == "<unset>"
    assert mask_value("short") == "*****"
    assert mask_value("sk-verylongsecret-123").startswith("sk-")
    assert "*" in mask_value("sk-verylongsecret-123")


def test_mask_env_value_only_sensitive_keys():
    assert "*" in mask_env_value("DEEPSEEK_API_KEY", "sk-secret")
    assert "sk-secret" not in mask_env_value("DEEPSEEK_API_KEY", "sk-secret")
    assert "*" in mask_env_value("LMSTUDIO_API_KEY", "lm-studio")
    assert mask_env_value("DEEPSEEK_MODEL", "deepseek-chat") == "deepseek-chat"
    assert mask_env_value("AUDIO_RENDERER", "fallback") == "fallback"
