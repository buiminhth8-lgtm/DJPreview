"""T28：演示示例 prompt 合法性测试。"""

import json
from pathlib import Path

from packages.music_core.styles.style_library import list_style_templates

DEMO_PROMPTS = Path(__file__).resolve().parents[1] / "examples" / "demo_prompts.json"


def _cases() -> list[dict]:
    return json.loads(DEMO_PROMPTS.read_text(encoding="utf-8"))


def test_demo_prompts_is_valid_json():
    cases = _cases()
    assert isinstance(cases, list)


def test_has_exactly_eight_cases():
    assert len(_cases()) == 8


def test_each_case_has_required_fields():
    for case in _cases():
        for field in ("id", "title", "prompt", "expected_style"):
            assert field in case, f"案例缺少字段 {field}: {case}"


def test_ids_unique():
    ids = [case["id"] for case in _cases()]
    assert len(ids) == len(set(ids))


def test_prompts_non_empty():
    for case in _cases():
        assert case["prompt"].strip(), case["id"]


def test_expected_style_matches_style_library():
    valid_ids = {template.id for template in list_style_templates()}
    for case in _cases():
        assert case["expected_style"] in valid_ids, (
            f"{case['id']} 的 expected_style={case['expected_style']!r} 不在风格库中"
        )
