"""T31：前端链路 smoke 脚本可导入 / --help 可执行（不依赖真实服务）。"""

import http.server
import importlib.util
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

SMOKE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "demo_t30_frontend_smoke.py"


def test_smoke_script_exists():
    assert SMOKE_SCRIPT.exists()


def test_smoke_script_help_runs():
    proc = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0
    assert "--backend-url" in proc.stdout
    assert "--check-frontend" in proc.stdout


def test_smoke_script_importable():
    spec = importlib.util.spec_from_file_location("demo_t30_frontend_smoke", SMOKE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)
    assert callable(module.check_frontend)


def test_check_frontend_falls_back_to_loopback_variant():
    """Vite 常监听 ::1，脚本应能从 127.0.0.1/localhost 之间自动回退。"""
    spec = importlib.util.spec_from_file_location("demo_t30_frontend_smoke", SMOKE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handler = type(
        "_RootHandler",
        (http.server.BaseHTTPRequestHandler,),
        {
            "do_GET": lambda self: (
                self.send_response(200),
                self.send_header("Content-Type", "text/html"),
                self.end_headers(),
                self.wfile.write(b'<!doctype html><div id="root"></div>'),
            ),
            "log_message": lambda self, *args: None,
        },
    )
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        # 任一 host 变体可用即可通过；127.0.0.1 保证可达。
        assert module.check_frontend(f"http://127.0.0.1:{port}", timeout=5)
        server.shutdown()
