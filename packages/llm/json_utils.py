"""LLM JSON 提取与解析工具。

支持：纯 JSON、```json 代码块、JSON 前后带少量解释文本。
只接受 JSON object；数组或其他类型会被明确拒绝。
"""

from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _iter_balanced_objects(text: str):
    """逐个产出文本中最外层平衡的 JSON object 子串（从第一个 { 开始）。"""
    idx = 0
    while True:
        start = text.find("{", idx)
        if start < 0:
            return
        depth = 0
        in_string = False
        escape = False
        end = -1
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end < 0:
            return
        yield text[start : end + 1]
        idx = end + 1


def extract_json_text(text: str) -> str:
    """从模型输出中提取 JSON object 的原始文本。

    失败（无 JSON、非法 JSON、数组输出等）时抛出 ValueError。
    """
    if text is None:
        raise ValueError("模型输出为空，无法提取 JSON")
    stripped = text.strip()
    if not stripped:
        raise ValueError("模型输出为空，无法提取 JSON")

    # 1) 整体就是合法 JSON：object 接受，数组明确拒绝
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        pass
    else:
        if isinstance(data, dict):
            return stripped
        raise ValueError("模型输出 JSON 不是 object（期望字典对象）")

    # 2) ```json 代码块（可能出现多个，逐个尝试）
    for match in _FENCE_RE.finditer(stripped):
        candidate = match.group(1).strip()
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return candidate
        raise ValueError("模型输出 JSON 不是 object（期望字典对象）")

    # 3) 带前后文本时提取第一个平衡 JSON object
    for candidate in _iter_balanced_objects(stripped):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return candidate

    raise ValueError("模型输出不是合法 JSON，且未找到可解析的 JSON 对象")


def extract_json_object(text: str) -> dict:
    """提取并解析 JSON object；失败或非 object 时抛出 ValueError。"""
    return json.loads(extract_json_text(text))
