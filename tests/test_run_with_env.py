"""T33：scripts/run_with_env.py 测试。"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_with_env.py"


def _run(*args):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(ROOT)
    # 避免 conftest 之外的 LLM_PROVIDER 干扰 profile 加载
    env.pop("LLM_PROVIDER", None)
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
    assert "--profile" in proc.stdout
    assert "--env-file" in proc.stdout


def test_print_env_mock_profile():
    proc = _run("--profile", "mock", "--print-env")
    assert proc.returncode == 0
    assert "Loaded env profile: mock" in proc.stdout


def test_unknown_profile_fails():
    proc = _run("--profile", "no_such_profile", "--print-env")
    assert proc.returncode == 1
    assert "未知的 LLM_ENV_PROFILE" in (proc.stdout + proc.stderr)


def test_run_command_passthrough():
    proc = _run("--profile", "mock", "--", sys.executable, "-c", "print('PASSTHROUGH_OK')")
    assert proc.returncode == 0
    assert "PASSTHROUGH_OK" in proc.stdout
