"""Prompt Registry：统一管理 prompts 目录下的提示词模板。"""

from __future__ import annotations

import re
from pathlib import Path

from packages.llm.prompt_versioning import compute_prompt_version

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PROMPTS_DIR = _PROJECT_ROOT / "prompts"

_REGISTRY = {
    "music_spec_generator": "music_spec_generator.md",
    "music_planner": "music_planner.md",
    "music_editor": "music_editor.md",
    "json_repair": "json_repair.md",
    "style_planner": "style_planner.md",
    "reference_planner": "reference_planner.md",
    "evaluation_prompt": "evaluation_prompt.md",
}

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class PromptRegistry:
    """prompts/ 目录下的提示词注册表。

    支持读取、简单变量渲染（{key} → value，不做 Jinja2）。
    变量缺失或 prompt 文件缺失时抛出清晰 ValueError。
    """

    def __init__(self, prompt_dir: Path | str | None = None) -> None:
        self.prompt_dir = Path(prompt_dir) if prompt_dir is not None else _PROMPTS_DIR

    def _prompt_path(self, name: str) -> Path:
        filename = _REGISTRY.get(name)
        if filename is None:
            raise ValueError(f"未知的 prompt 模板：{name}（支持 {sorted(_REGISTRY)}）")
        return self.prompt_dir / filename

    def list_prompts(self) -> list[str]:
        """返回已注册的 prompt 名称列表。"""
        return sorted(_REGISTRY)

    def get_prompt(self, name: str) -> str:
        """读取 prompt 模板内容；文件缺失抛清晰错误。"""
        path = self._prompt_path(name)
        if not path.exists():
            raise ValueError(f"prompt 文件不存在：{path}")
        return path.read_text(encoding="utf-8")

    def get_prompt_version(self, name: str) -> str:
        """返回 prompt 模板当前版本（内容哈希前 8 位）。"""
        return compute_prompt_version(self.get_prompt(name))

    def render_prompt(self, name: str, variables: dict[str, object] | None = None) -> str:
        """渲染 prompt：把 {key} 替换为变量值；未提供的占位符报错。"""
        content = self.get_prompt(name)
        for key, value in (variables or {}).items():
            content = content.replace("{" + key + "}", str(value))
        leftovers = sorted(
            {
                placeholder
                for placeholder in _PLACEHOLDER_RE.findall(content)
                if placeholder not in (variables or {})
            }
        )
        if leftovers:
            raise ValueError(f"prompt {name} 缺少变量：{leftovers}")
        return content


_DEFAULT_REGISTRY = PromptRegistry()


def list_prompts() -> list[str]:
    """返回已注册的 prompt 名称列表。"""
    return _DEFAULT_REGISTRY.list_prompts()


def get_prompt(name: str) -> str:
    """读取 prompt 模板内容；文件缺失抛清晰错误。"""
    return _DEFAULT_REGISTRY.get_prompt(name)


def get_prompt_version(name: str) -> str:
    """返回 prompt 模板当前版本（内容哈希前 8 位）。"""
    return _DEFAULT_REGISTRY.get_prompt_version(name)


def render_prompt(name: str, variables: dict[str, object] | None = None) -> str:
    """渲染 prompt：把 {key} 替换为变量值；缺失变量报错。"""
    return _DEFAULT_REGISTRY.render_prompt(name, variables)
