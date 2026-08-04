"""Prompt Registry：统一管理 prompts 目录下的提示词模板。"""

from __future__ import annotations

from pathlib import Path

from packages.llm.prompt_versioning import compute_prompt_version

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _PROJECT_ROOT / "prompts"

_REGISTRY = {
    "music_planner": "music_planner.md",
    "music_editor": "music_editor.md",
    "style_planner": "style_planner.md",
    "reference_planner": "reference_planner.md",
    "evaluation_prompt": "evaluation_prompt.md",
}


def _prompt_path(name: str) -> Path:
    filename = _REGISTRY.get(name)
    if filename is None:
        raise ValueError(f"未知的 prompt 模板：{name}（支持 {sorted(_REGISTRY)}）")
    return _PROMPTS_DIR / filename


def list_prompts() -> list[str]:
    """返回已注册的 prompt 名称列表。"""
    return sorted(_REGISTRY)


def get_prompt(name: str) -> str:
    """读取 prompt 模板内容；文件缺失抛清晰错误。"""
    path = _prompt_path(name)
    if not path.exists():
        raise ValueError(f"prompt 文件不存在：{path}")
    return path.read_text(encoding="utf-8")


def get_prompt_version(name: str) -> str:
    """返回 prompt 模板当前版本（内容哈希前 8 位）。"""
    return compute_prompt_version(get_prompt(name))


def render_prompt(name: str, variables: dict) -> str:
    """渲染 prompt：把 {key} 替换为变量值；缺失变量报错。"""
    content = get_prompt(name)
    missing = []
    for key in variables:
        content = content.replace("{" + key + "}", str(variables[key]))
    # 检查未替换的占位符
    import re

    leftovers = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", content)
    if leftovers:
        raise ValueError(f"prompt {name} 缺少变量：{sorted(set(leftovers))}")
    return content
