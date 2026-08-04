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
