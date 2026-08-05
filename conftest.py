"""pytest 全局配置：保证项目根目录可导入，并固定使用 MockProvider + 独立测试数据目录。"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("PROJECTS_DIR", str(ROOT / "data" / "test_projects"))
# 测试环境强制使用 fallback 渲染器，避免依赖系统 FluidSynth
os.environ.setdefault("AUDIO_RENDERER", "fallback")


def pytest_collection_modifyitems(config, items):
    """测试分层：模块级使用 fastapi TestClient 的用例自动标记为 slow（集成测试）。

    快速回归用 `pytest -m "not slow"`；全量回归用 `pytest -m slow` 或直接 `pytest`。
    """
    for item in items:
        module = getattr(item, "module", None)
        client = getattr(module, "client", None)
        if client is None:
            continue
        # 仅识别 Starlette/FastAPI TestClient（避免误标其他同名属性）
        if client.__class__.__module__.startswith(("fastapi.testclient", "starlette.testclient")):
            item.add_marker("slow")
