"""LLM 结构化输出：解析、校验与二次修复。"""

from __future__ import annotations

from typing import Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

from packages.llm.json_utils import extract_json_object

T = TypeVar("T", bound=BaseModel)


class LLMConfigurationError(ValueError):
    """LLM 配置缺失（如 API Key 未配置）。"""


class LLMAPIError(RuntimeError):
    """LLM API 网络 / HTTP 调用失败。"""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMOutputError(ValueError):
    """模型输出无法解析或不符合 schema。"""

    def __init__(self, message: str, *, task_name: str | None = None) -> None:
        super().__init__(message)
        self.task_name = task_name


RepairFn = Callable[[str, str], str]


def parse_structured_response(
    response_model: Type[T],
    raw_text: str,
    *,
    repair_fn: RepairFn | None = None,
    retries: int = 2,
    task_name: str | None = None,
) -> T:
    """解析并校验模型输出；失败时调用 repair_fn 修复，最多重试 retries 次。

    修复回调签名：repair_fn(raw_output: str, error_text: str) -> str（返回新的模型输出）。
    最终仍失败时抛出 LLMOutputError；修复调用本身失败则直接向上抛出。
    """
    last_error: Exception | None = None
    current = raw_text
    for attempt in range(retries + 1):
        try:
            data = extract_json_object(current)
            return response_model.model_validate(data)
        except (ValueError, ValidationError) as exc:
            last_error = exc
            if attempt >= retries or repair_fn is None:
                break
            try:
                current = repair_fn(current, str(exc))
            except LLMAPIError:
                raise
            except Exception as exc2:  # noqa: BLE001 - 修复失败按输出错误处理
                last_error = exc2
                break
    raise LLMOutputError(
        f"模型输出解析失败（task={task_name}）：{last_error}",
        task_name=task_name,
    ) from last_error
