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


def test_unknown_provider_fails():
    proc = _run("--provider", "no_such_provider")
    assert proc.returncode == 1
    assert "未知的 provider" in proc.stdout or "未知的 provider" in proc.stderr


def test_mock_mode_runs():
    proc = _run("--provider", "mock")
    assert proc.returncode == 0
    assert "[provider] mock" in proc.stdout


def test_importable():
    import importlib.util

    spec = importlib.util.spec_from_file_location("test_llm_provider", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
