"""T28：演示 smoke 脚本可导入 / --help 可执行（不依赖真实后端）。"""

import importlib.util
import subprocess
import sys
from pathlib import Path

SMOKE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo_t28_smoke.py"


def test_smoke_script_exists():
    assert SMOKE_SCRIPT.exists()


def test_smoke_script_help_runs():
    proc = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "--base-url" in proc.stdout
    assert "--all" in proc.stdout
    assert "--provider" in proc.stdout


def test_smoke_script_importable():
    spec = importlib.util.spec_from_file_location("demo_t28_smoke", SMOKE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
    assert callable(module.load_prompts)
