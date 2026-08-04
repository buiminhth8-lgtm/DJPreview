"""Prompt 版本管理（内容哈希）。"""

from __future__ import annotations

import hashlib


def compute_prompt_version(content: str) -> str:
    """返回 prompt 内容的短哈希版本号。"""
    return hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
