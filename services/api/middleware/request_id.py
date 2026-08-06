"""Request ID 中间件（纯 ASGI）。

每个请求生成 request_id（优先复用 X-Request-ID 请求头），写入 scope.state 与
contextvar，供路由、异常处理器与 LLM Provider 使用；并在响应头与 JSON 响应体中注入。

实现说明：为在 JSON 响应体中注入 request_id 且保证 content-length 正确，
对 JSON 响应做 body 缓冲；非 JSON（如文件流）直接透传并在响应头加 X-Request-ID。
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from packages.llm.trace import reset_request_id, set_request_id

SendCallable = Callable[[Message], Awaitable[None]]

_JSON_CONTENT_TYPES = ("application/json", "application/problem+json")


def _content_type(headers) -> str:
    for name, value in headers or []:
        if name.lower() == b"content-type":
            return value.decode("latin-1", errors="replace")
    return ""


class RequestIdMiddleware:
    """为每个请求分配 / 透传 request_id，并写入响应头与 JSON 响应体。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers") or []
        incoming = next(
            (v.decode("latin-1", errors="replace") for k, v in headers if k.lower() == b"x-request-id"),
            None,
        )
        request_id = incoming or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = set_request_id(request_id)

        start_message: Message | None = None
        chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start_message, chunks
            if message["type"] == "http.response.start":
                start_message = message
                return

            if message["type"] == "http.response.body":
                if start_message is None:
                    # 理论上不应出现：没有 start 直接 body
                    await send(message)
                    return

                ctype = _content_type(start_message["headers"])
                is_json = any(ctype.startswith(c) for c in _JSON_CONTENT_TYPES)
                chunks.append(message.get("body", b""))
                more = message.get("more_body", False)

                if not more:
                    # 拿到完整 body 后统一发送
                    if is_json:
                        try:
                            data = json.loads(b"".join(chunks))
                        except (ValueError, TypeError):
                            data = None
                        if isinstance(data, dict) and "request_id" not in data:
                            data["request_id"] = request_id
                            new_body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                            headers_out = [
                                (k, v) for k, v in start_message["headers"] if k.lower() != b"content-length"
                            ]
                            headers_out.append((b"content-length", str(len(new_body)).encode("latin-1")))
                            start_message = {
                                **start_message,
                                "headers": headers_out,
                            }
                            chunks = [new_body]
                    final_headers = [
                        (k, v)
                        for k, v in start_message["headers"]
                        if k.lower() != b"x-request-id"
                    ]
                    final_headers.append((b"x-request-id", request_id.encode("latin-1")))
                    start_message = {**start_message, "headers": final_headers}
                    await send(start_message)
                    await send({"type": "http.response.body", "body": b"".join(chunks), "more_body": False})
                    start_message = None
                    chunks = []
                return

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_request_id(token)
