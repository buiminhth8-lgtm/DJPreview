"""T32：scripts/test_llm_provider.py 脚本测试。"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test_llm_provider.py"


def _run(*args):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT)
    # 固定为 mock，避免被项目 .env（可能含 deepseek key）污染，保证确定性
    env["LLM_PROVIDER"] = "mock"
    env.pop("LLM_ENV_PROFILE", None)
    env.pop("LLM_ENV_FILE", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_script_exists():
    assert SCRIPT.exists()


def test_help_runs():
    proc = _run("--help")
    assert proc.returncode == 0
    assert "--provider" in proc.stdout
    assert "--base-url" in proc.stdout
    assert "--profile" in proc.stdout


def test_unknown_provider_fails():
    proc = _run("--provider", "no_such_provider")
    assert proc.returncode == 1
    assert "未知的 provider" in proc.stdout or "未知的 provider" in proc.stderr


def test_mock_mode_runs():
    proc = _run("--provider", "mock")
    assert proc.returncode == 0
    assert "[provider] mock" in proc.stdout


def test_profile_mock_runs():
    proc = _run("--profile", "mock")
    assert proc.returncode == 0
    assert "Loaded env profile: mock" in proc.stdout
    assert "[provider] mock" in proc.stdout


def test_profile_lmstudio_reports_unreachable(tmp_path):
    """lmstudio profile 指向不可达端口时给出清晰提示（not reachable），不崩溃。"""
    env_file = tmp_path / ".lmstudio_local.env"
    env_file.write_text(
        "LLM_PROVIDER=lmstudio\n"
        "LMSTUDIO_BASE_URL=http://127.0.0.1:9/v1\n"
        "LMSTUDIO_MODEL=local\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT)
    env["LLM_ENV_FILE"] = str(env_file)
    env.pop("LLM_PROVIDER", None)  # 移除 conftest 的 mock，让 profile 文件生效
    env.pop("LLM_ENV_PROFILE", None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--profile", "lmstudio"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert "Loaded env profile: lmstudio" in proc.stdout
    assert "not reachable" in (proc.stdout + proc.stderr)
    assert "Loaded env files: .env" in proc.stdout


def test_importable():
    import importlib.util

    spec = importlib.util.spec_from_file_location("test_llm_provider", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
