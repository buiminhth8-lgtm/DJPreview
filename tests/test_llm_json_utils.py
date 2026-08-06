"""T11：LLM JSON 提取与解析工具测试。"""

import json

import pytest

from packages.llm.json_utils import clean_jsonc, extract_json_object, extract_json_text


def test_pure_json():
    text = '{"a": 1, "b": [1, 2]}'
    assert extract_json_object(text) == {"a": 1, "b": [1, 2]}


def test_json_fence():
    text = "```json\n{\"a\": 1}\n```"
    assert extract_json_object(text) == {"a": 1}


def test_json_fence_without_language_tag():
    text = "```\n{\"a\": 1}\n```"
    assert extract_json_object(text) == {"a": 1}


def test_text_around_json():
    text = '好的，这是结果：{"a": 1, "b": {"c": 2}} 希望对你有帮助。'
    assert extract_json_object(text) == {"a": 1, "b": {"c": 2}}


def test_invalid_json_raises():
    with pytest.raises(ValueError):
        extract_json_object("这不是 JSON")


def test_empty_string_raises():
    with pytest.raises(ValueError):
        extract_json_object("   ")
    with pytest.raises(ValueError):
        extract_json_object("")


def test_array_output_rejected():
    with pytest.raises(ValueError, match="不是 object"):
        extract_json_object('[{"a": 1}]')


def test_scalar_output_rejected():
    with pytest.raises(ValueError, match="不是 object"):
        extract_json_object("42")


def test_extract_json_text_returns_parseable_slice():
    text = '前言 {"a": 1} 后语'
    extracted = extract_json_text(text)
    assert json.loads(extracted) == {"a": 1}


def test_trailing_comma_accepted():
    text = '{"a": 1, "b": [1, 2,],}'
    assert extract_json_object(text) == {"a": 1, "b": [1, 2]}


def test_line_comment_accepted():
    text = '{"a": 1, // comment\n "b": 2}'
    assert extract_json_object(text) == {"a": 1, "b": 2}


def test_block_comment_accepted():
    text = '{"a": 1 /* block */, "b": 2}'
    assert extract_json_object(text) == {"a": 1, "b": 2}


def test_clean_jsonc_preserves_strings():
    text = '{"a": "http://x.com", "b": "/* not a comment */"}'
    assert extract_json_object(text) == {"a": "http://x.com", "b": "/* not a comment */"}


def test_clean_jsonc_function():
    assert clean_jsonc('{"a": 1, // hi\n "b": 2,}') == '{"a": 1, \n "b": 2}'


def test_bom_handled():
    text = '\ufeff{"a": 1}'
    assert extract_json_object(text) == {"a": 1}


def test_fence_with_trailing_comma():
    text = '```json\n{"a": 1, "b": 2,}\n```'
    assert extract_json_object(text) == {"a": 1, "b": 2}


def test_error_message_includes_snippet():
    with pytest.raises(ValueError, match="不是合法 JSON"):
        extract_json_object("完全不是 JSON 的内容")
