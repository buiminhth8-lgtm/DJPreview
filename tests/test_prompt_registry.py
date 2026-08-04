"""T11：Prompt Registry 单元测试。"""

import pytest

from packages.llm.prompt_registry import PromptRegistry, get_prompt, list_prompts, render_prompt


def test_registry_contains_t11_prompts():
    names = list_prompts()
    assert "music_spec_generator" in names
    assert "music_editor" in names
    assert "json_repair" in names


def test_get_existing_prompt():
    for name in ("music_spec_generator", "music_editor", "json_repair"):
        content = get_prompt(name)
        assert isinstance(content, str)
        assert content.strip()


def test_unknown_prompt_raises():
    with pytest.raises(ValueError, match="未知的 prompt"):
        get_prompt("does_not_exist")


def test_missing_prompt_file_raises(tmp_path):
    registry = PromptRegistry(prompt_dir=tmp_path)
    with pytest.raises(ValueError, match="prompt 文件不存在"):
        registry.get_prompt("music_editor")


def test_render_prompt_variables():
    rendered = render_prompt(
        "music_editor",
        {"music_spec": '{"version": "0.1"}', "instruction": "副歌更亮一点"},
    )
    assert "副歌更亮一点" in rendered
    assert '{"version": "0.1"}' in rendered


def test_render_prompt_missing_variable_raises():
    with pytest.raises(ValueError, match="缺少变量"):
        render_prompt("music_editor", {"music_spec": "{}"})
