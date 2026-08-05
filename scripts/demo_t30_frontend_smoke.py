#!/usr/bin/env python3
"""T31 前端链路 smoke 脚本（可选）。

覆盖：health → 生成 MusicSpec → 同步 MIDI → 同步 WAV → 版本列表 →
异步 render-audio 任务（轮询到终态）→ assets；可选探活前端 dev server。
只做 HTTP 检查，不落盘生成资产；基础链路失败时 exit 1。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


class ApiFailure(RuntimeError):
    """API 请求失败。"""


def request_json(base_url: str, method: str, path: str, payload: dict | None = None, timeout: int = 60):
    url = base_url.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return raw
    except urllib.error.HTTPError as exc:
        raise ApiFailure(f"{method} {path} -> HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ApiFailure(f"{method} {path} -> 网络错误：{exc.reason}") from exc


def wait_task(base_url: str, task_id: str, timeout: int = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = request_json(base_url, "GET", f"/api/v1/tasks/{task_id}")
        if task["status"] in ("succeeded", "failed", "cancelled"):
            return task
        time.sleep(0.5)
    raise ApiFailure(f"任务 {task_id} 未在 {timeout}s 内结束")


def check_frontend(frontend_url: str, timeout: int = 10) -> bool:
    """探活前端 dev server：HTTP 200 且页面含 root 挂载点。

    Vite 默认监听 localhost（可能解析为 IPv6 ::1），而 127.0.0.1 可能无法直连；
    因此给定地址失败时自动尝试另一 host 变体，避免误报。
    """
    candidates = [frontend_url]
    for host in ("127.0.0.1", "localhost", "[::1]"):
        if host in frontend_url:
            other = "localhost" if host != "localhost" else "127.0.0.1"
            candidates.append(frontend_url.replace(host, other, 1))
    for url in candidates:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                if resp.status != 200:
                    continue
                head = resp.read(8192).decode("utf-8", errors="ignore")
                if 'id="root"' in head:
                    return True
        except Exception:  # noqa: BLE001 - 单个地址失败则尝试下一个
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ai-music-mvp T31 前端链路 smoke（后端全链路 + 可选前端探活）",
    )
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="后端 API 地址")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173", help="前端 dev server 地址")
    parser.add_argument("--prompt", default="生成一段忧郁空灵的钢琴配乐", help="演示 prompt")
    parser.add_argument("--check-frontend", action="store_true", help="同时探活前端 dev server")
    args = parser.parse_args(argv)

    checks: dict[str, str] = {}
    try:
        request_json(args.backend_url, "GET", "/api/v1/health")
        checks["health"] = "ok"

        song = request_json(args.backend_url, "POST", "/api/v1/songs/generate", {"prompt": args.prompt})
        song_id = song.get("song_id")
        checks["generate"] = "ok" if song_id and song.get("music_spec") else "failed（缺 song_id/music_spec）"
        if not song_id:
            raise ApiFailure("生成歌曲失败：未返回 song_id")

        request_json(args.backend_url, "POST", f"/api/v1/songs/{song_id}/midi/generate")
        checks["midi_sync"] = "ok"

        request_json(args.backend_url, "POST", f"/api/v1/songs/{song_id}/audio/render")
        checks["audio_sync"] = "ok"

        request_json(args.backend_url, "GET", f"/api/v1/songs/{song_id}/versions")
        checks["versions"] = "ok"

        task = request_json(args.backend_url, "POST", f"/api/v1/songs/{song_id}/tasks/render-audio")
        final = wait_task(args.backend_url, task["task_id"])
        checks["async_task"] = (
            "ok" if final["status"] == "succeeded" else f"failed（{final['status']}）"
        )

        assets = request_json(args.backend_url, "GET", f"/api/v1/songs/{song_id}/assets")
        checks["assets_has_audio"] = "ok" if assets.get("has_audio") else "failed"

        if args.check_frontend:
            checks["frontend"] = "ok" if check_frontend(args.frontend_url) else "failed（dev server 未启动或页面异常）"
    except ApiFailure as exc:
        checks["error"] = str(exc)

    print(f"[T31 smoke] 后端: {args.backend_url}  前端探活: {args.check_frontend}")
    for name, value in checks.items():
        print(f"    - {name}: {value}")
    ok = all(value.startswith("ok") for value in checks.values())
    print("[T31 smoke] 结果:", "通过" if ok else "失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
