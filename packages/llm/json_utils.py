"""LLM JSON 提取与解析工具。

支持：
  - 纯 JSON
  - ```json 代码块（含不带语言标签的围栏）
  - JSON 前后带解释文本（取第一个完整 JSON object）
  - JSONC 风格的行/块注释与尾随逗号（本地模型常见输出，字符串感知去除）
只接受 JSON object；数组或其他类型会被明确拒绝。
"""

from __future__ import annotations

import json
import re

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def clean_jsonc(text: str) -> str:
    """去除 JSONC 风格的行注释（//）、块注释（/* */）与尾随逗号。

    逐字符扫描，跳过字符串字面量，不会破坏字符串内容中的注释符号。
    """
    out: list[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\":
                i += 1
                if i < n:
                    out.append(text[i])
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i = min(i + 2, n)
                continue
        if ch == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1  # 尾随逗号：跳过
                continue
        out.append(ch)
        i += 1
    return "".join(out)


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


def _is_whole_json(stripped: str) -> tuple[bool, dict | None]:
    """整体是否可解析为 JSON。返回 (是否为完整 JSON, 解析结果)。"""
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return False, None
    return True, data


def _parseable_text(candidate: str) -> str | None:
    """返回可直接 json.loads 为 object 的文本；必要时返回 JSONC 清洗后的版本。

    无法解析为非 dict 时返回 None。
    """
    stripped = candidate.strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        cleaned = clean_jsonc(stripped)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    else:
        cleaned = stripped
    return cleaned if isinstance(data, dict) else None


def _parse_dict(candidate: str) -> dict | None:
    """尝试把候选文本解析为 JSON object；支持 JSONC 清洗后二次尝试。"""
    text = _parseable_text(candidate)
    if text is None:
        return None
    return json.loads(text)


def _looks_like_json_object(candidate: str) -> bool:
    """粗略判断候选是否像 JSON（数组 / 标量等非 object 输出）。"""
    stripped = candidate.strip()
    return stripped.startswith(("[", "{", '"', "-", "t", "f", "n"))


def extract_json_text(text: str) -> str:
    """从模型输出中提取 JSON object 的原始文本（保证可被 json.loads 解析）。

    失败（无 JSON、非法 JSON、数组输出等）时抛出 ValueError。
    """
    if text is None:
        raise ValueError("模型输出为空，无法提取 JSON")
    stripped = text.strip().lstrip("\ufeff").strip()
    if not stripped:
        raise ValueError("模型输出为空，无法提取 JSON")

    # 1) 整体就是合法 JSON：object 接受，数组/标量明确拒绝
    is_whole, whole = _is_whole_json(stripped)
    if is_whole:
        if isinstance(whole, dict):
            return stripped
        raise ValueError("模型输出 JSON 不是 object（期望字典对象）")

    # 2) 整体不是合法 JSON，但 JSONC 清洗后是 object（尾随逗号 / 注释）
    whole_clean = _parseable_text(stripped)
    if whole_clean is not None:
        return whole_clean

    # 3) ```json 代码块（可能出现多个，逐个尝试）
    for match in _FENCE_RE.finditer(stripped):
        candidate = match.group(1).strip()
        parsed = _parseable_text(candidate)
        if parsed is not None:
            return parsed
        if _looks_like_json_object(candidate):
            raise ValueError("模型输出 JSON 不是 object（期望字典对象）")

    # 4) 带前后文本时提取第一个平衡 JSON object
    for candidate in _iter_balanced_objects(stripped):
        parsed = _parseable_text(candidate)
        if parsed is not None:
            return parsed

    raise ValueError(
        "模型输出不是合法 JSON，且未找到可解析的 JSON 对象"
        f"（原文片段：{stripped[:200]!r}）"
    )


def extract_json_object(text: str) -> dict:
    """提取并解析 JSON object；失败或非 object 时抛出 ValueError。"""
    return json.loads(extract_json_text(text))
