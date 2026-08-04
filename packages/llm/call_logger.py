"""LLM 调用日志记录器。

有 project_id：{base_dir}/{project_id}/llm_calls/{timestamp}_{task_name}.json
无 project_id：{base_dir.parent}/llm_calls/{timestamp}_{task_name}.json
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.llm.models import LLMCallRecord

logger = logging.getLogger(__name__)

DEFAULT_BASE_DIR = Path("data/projects")
_SENSITIVE_KEYS = (
    "api_key",
    "authorization",
    "proxy-authorization",
    "x-api-key",
)
_FILENAME_SAFE = re.compile(r"[^0-9A-Za-z_-]")


def _sanitize(value: Any) -> Any:
    """递归移除敏感字段，避免 API Key / Authorization 写入日志。"""
    if isinstance(value, dict):
        return {
            str(k): _sanitize(v)
            for k, v in value.items()
            if str(k).lower() not in _SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    return value


class LLMCallLogger:
    """把 LLM 调用记录为 UTF-8 JSON 文件；写日志失败不影响主流程。"""

    def __init__(self, base_dir: Path | str = DEFAULT_BASE_DIR) -> None:
        self.base_dir = Path(base_dir)

    def _target_dir(self, project_id: str | None) -> Path:
        if project_id:
            safe_id = _FILENAME_SAFE.sub("_", project_id)
            return self.base_dir / safe_id / "llm_calls"
        return self.base_dir.parent / "llm_calls"

    def log_call(
        self,
        *,
        project_id: str | None,
        task_name: str,
        provider: str,
        model: str,
        request: dict,
        response: dict | None = None,
        parsed: dict | None = None,
        error: str | None = None,
        latency_ms: int | None = None,
    ) -> Path | None:
        """记录一次调用；成功返回日志路径，失败返回 None（不影响主流程）。"""
        try:
            record = LLMCallRecord(
                project_id=project_id,
                task_name=task_name,
                provider=provider,
                model=model,
                request=_sanitize(request),
                response=_sanitize(response),
                parsed=_sanitize(parsed),
                error=error,
                latency_ms=latency_ms,
            )
            target_dir = self._target_dir(project_id)
            target_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            safe_task = _FILENAME_SAFE.sub("_", task_name) or "llm_call"
            path = target_dir / f"{timestamp}_{safe_task}.json"
            path.write_text(
                json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return path
        except Exception as exc:  # noqa: BLE001 - 日志失败不应阻断主流程
            logger.warning("LLM 调用日志写入失败：%s", exc)
            return None
