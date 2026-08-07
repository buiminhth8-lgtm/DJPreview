"""T39-B：SoundFont 渲染链路诊断 / fallback_reason / FluidSynth 检测测试。

使用 monkeypatch 模拟 FluidSynth 可用 / 不可用，不依赖真实安装。
"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _auto_renderer(monkeypatch):
    """强制 AUDIO_RENDERER=auto（避免 .mock.env 的 fallback 通过 settings 缓存泄漏）。"""
    monkeypatch.setenv("AUDIO_RENDERER", "auto")
    from services.api.dependencies.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(
        "services.api.routes.songs.get_settings",
        lambda: settings.model_copy(update={"audio_renderer": "auto"}),
    )


def _create_song(prompt: str = "生成一段忧郁空灵的钢琴配乐") -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _make_fake_sf2(tmp_path, name: str = "FakeSound.sf2") -> str:
    """生成一个合法 RIFF 头的假 .sf2 文件（< 1MB 但 header 正确）。"""
    path = tmp_path / name
    path.write_bytes(b"RIFF" + b"\x00" * 256)
    return str(path)


def test_validate_soundfont_file_missing(tmp_path, monkeypatch):
    from packages.renderer.fluidsynth_check import validate_soundfont_file

    status = validate_soundfont_file(tmp_path / "nope.sf2")
    assert status["exists"] is False
    assert status["valid"] is False
    assert status["error"] == "soundfont_file_missing"


def test_validate_soundfont_file_valid(tmp_path):
    from packages.renderer.fluidsynth_check import validate_soundfont_file

    path = _make_fake_sf2(tmp_path)
    status = validate_soundfont_file(path)
    assert status["exists"] is True
    assert status["valid"] is True
    assert status["format"] == ".sf2"
    assert status["error"] is None


def test_validate_soundfont_file_invalid_header(tmp_path):
    from packages.renderer.fluidsynth_check import validate_soundfont_file

    path = tmp_path / "Bad.sf2"
    path.write_bytes(b"NOTRIFF" + b"\x00" * 8)
    status = validate_soundfont_file(str(path))
    assert status["exists"] is True
    assert status["valid"] is False
    assert "RIFF" in (status["error"] or "")


def test_detect_fluidsynth_not_in_path(monkeypatch):
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    monkeypatch.delenv("FLUIDSYNTH_BIN", raising=False)
    monkeypatch.delenv("FLUIDSYNTH_PATH", raising=False)
    monkeypatch.setattr("packages.renderer.fluidsynth_check.shutil.which", lambda name: None)

    status = detect_fluidsynth()
    assert status["available"] is False
    assert status["error"] == "fluidsynth not found in PATH"


def test_detect_fluidsynth_available(monkeypatch, tmp_path):
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", str(fake_bin))

    calls: list[list[str]] = []

    def fake_run(cmd, *a, **k):
        calls.append(cmd)
        return type("P", (), {"returncode": 0, "stdout": "FluidSynth 2.3.0", "stderr": ""})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is True
    assert status["version"] == "FluidSynth 2.3.0"
    assert status["version_arg"] == "-V"
    assert status["error"] is None
    # 优先尝试 -V，不依赖 --version
    assert calls[0][-1] == "-V"


def test_detect_fluidsynth_version_flag_fails_v_succeeds(monkeypatch, tmp_path):
    """--version 报 Unknown switch 但 -V 成功 → available true。"""
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", str(fake_bin))

    calls: list[list[str]] = []

    def fake_run(cmd, *a, **k):
        calls.append(cmd)
        if cmd[-1] == "-V":
            return type("P", (), {"returncode": 0, "stdout": "FluidSynth runtime version 2.4.7", "stderr": ""})()
        return type("P", (), {"returncode": 1, "stdout": "", "stderr": "Unknown switch '-'"})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is True
    assert status["version"] == "FluidSynth runtime version 2.4.7"
    assert status["version_arg"] == "-V"
    assert status["error"] is None
    assert calls == [[str(fake_bin), "-V"]]


def test_detect_fluidsynth_v_fails_version_succeeds(monkeypatch, tmp_path):
    """-V 失败但 --version 成功 → available true。"""
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", str(fake_bin))

    calls: list[list[str]] = []

    def fake_run(cmd, *a, **k):
        calls.append(cmd)
        if cmd[-1] == "-V":
            return type("P", (), {"returncode": 2, "stdout": "", "stderr": "bad switch"})(  # noqa: S106
            )
        return type("P", (), {"returncode": 0, "stdout": "FluidSynth 2.3.1", "stderr": ""})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is True
    assert status["version"] == "FluidSynth 2.3.1"
    assert status["version_arg"] == "--version"
    assert status["error"] is None
    assert len(status["version_check_errors"]) == 1
    assert status["version_check_errors"][0]["arg"] == "-V"


def test_detect_fluidsynth_both_fail(monkeypatch, tmp_path):
    """-V 与 --version 都失败 → available false，并记录 version_check_errors。"""
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", str(fake_bin))

    def fake_run(cmd, *a, **k):
        return type("P", (), {"returncode": 1, "stdout": "", "stderr": "Unknown switch '-'"})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is False
    assert status["version"] is None
    assert status["version_arg"] is None
    assert len(status["version_check_errors"]) == 2
    assert [e["arg"] for e in status["version_check_errors"]] == ["-V", "--version"]
    assert "version check failed" in (status["error"] or "")


def test_detect_fluidsynth_bin_uses_which_for_bare_name(monkeypatch, tmp_path):
    """FLUIDSYNTH_BIN=fluidsynth（裸命令名）→ 用 shutil.which 解析真实路径。"""
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", "fluidsynth")
    monkeypatch.setattr("packages.renderer.fluidsynth_check.shutil.which", lambda name: str(fake_bin))

    def fake_run(cmd, *a, **k):
        return type("P", (), {"returncode": 0, "stdout": "FluidSynth 2.4.7", "stderr": ""})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is True
    assert status["binary"] == str(fake_bin)
    assert status["version_arg"] == "-V"


def test_detect_fluidsynth_timeout_used(monkeypatch, tmp_path):
    """版本检测命令必须设置 timeout。"""
    from packages.renderer.fluidsynth_check import detect_fluidsynth

    fake_bin = tmp_path / "fluidsynth.exe"
    fake_bin.write_bytes(b"MZfake")
    monkeypatch.setenv("FLUIDSYNTH_BIN", str(fake_bin))

    seen_timeouts: list[float] = []

    def fake_run(cmd, *a, **k):
        seen_timeouts.append(k.get("timeout"))
        return type("P", (), {"returncode": 1, "stdout": "", "stderr": "fail"})()

    monkeypatch.setattr("packages.renderer.fluidsynth_check.subprocess.run", fake_run)
    status = detect_fluidsynth()
    assert status["available"] is False
    assert all(t is not None for t in seen_timeouts)
    assert all(t > 0 for t in seen_timeouts)


def test_render_command_uses_ni_and_no_shell(tmp_path, monkeypatch):
    """渲染命令包含 -ni、list 参数、不 shell 拼接、含 soundfont 与 midi 路径，且选项在 positional 之前。"""
    from packages.renderer.fluidsynth_renderer import FluidSynthRenderer

    soundfont = _make_fake_sf2(tmp_path, "GeneralUser-GS.sf2")
    midi = tmp_path / "input.mid"
    midi.write_bytes(b"MThd" + b"\x00" * 20)
    wav = tmp_path / "out.wav"

    captured: dict = {}

    def fake_detect():
        return {"available": True, "binary": "fluidsynth", "version": "2.4.7", "error": None}

    def fake_run(cmd, capture_output=True, text=True, timeout=None, shell=None):
        captured["cmd"] = cmd
        captured["shell"] = shell
        # 生成合法 WAV 文件
        import wave

        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 441)
        return type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(
        "packages.renderer.fluidsynth_renderer.detect_fluidsynth", fake_detect
    )
    monkeypatch.setattr("packages.renderer.fluidsynth_renderer.subprocess.run", fake_run)

    renderer = FluidSynthRenderer()
    result = renderer.render_wav(midi, wav, soundfont_path=soundfont)
    assert result.renderer == "fluidsynth"
    assert "-ni" in captured["cmd"]
    assert str(soundfont) in captured["cmd"]
    assert str(midi) in captured["cmd"]
    assert "-F" in captured["cmd"]
    assert "-r" in captured["cmd"]
    assert captured["shell"] is None or captured["shell"] is False
    assert all(isinstance(c, str) for c in captured["cmd"])
    # 选项（-ni/-F/-r/-g）必须在 positional（soundfont/midi）之前，避免 Windows 下卡住
    flags = set(captured["cmd"]) & {"-ni", "-F", "-r", "-g"}
    first_pos = captured["cmd"].index(str(soundfont))
    for flag in flags:
        assert captured["cmd"].index(flag) < first_pos, f"{flag} 必须在 positional 参数之前"


def test_render_fallback_reason_fluidsynth_unavailable(tmp_path, monkeypatch):
    """SoundFont 有效但 FluidSynth 不可用 → fallback_reason=fluidsynth_unavailable。"""
    from packages.music_core.audio.soundfont_manager import _info_from_path
    from pathlib import Path as _Path

    sf = _info_from_path(_Path(_make_fake_sf2(tmp_path)))

    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.detect_fluidsynth",
        lambda: {"available": False, "binary": None, "version": None, "error": "fluidsynth not found in PATH"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: sf)
    monkeypatch.setattr("services.api.routes.songs.resolve_default_soundfont", lambda: sf)

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["renderer"] == "fallback"
    assert meta["is_fallback"] is True
    assert meta["fallback_reason"] == "fluidsynth_unavailable"


def test_render_fallback_reason_no_soundfont_selected(monkeypatch):
    """没有选择任何 SoundFont → fallback_reason=no_soundfont_selected。"""
    _auto_renderer(monkeypatch)
    monkeypatch.setattr("services.api.routes.songs.get_project_soundfont", lambda _sid: None)
    monkeypatch.setattr("services.api.routes.songs.resolve_default_soundfont", lambda: None)

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["renderer"] == "fallback"
    assert meta["is_fallback"] is True
    assert meta["fallback_reason"] == "no_soundfont_selected"


def test_render_fallback_reason_soundfont_not_found(monkeypatch):
    """项目指定 soundfont_id 但本地查不到 → fallback_reason=soundfont_not_found。"""
    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.get_project_soundfont",
        lambda _sid: {"soundfont_id": "deadbeef", "soundfont_name": "Missing"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: None)
    monkeypatch.setattr("services.api.routes.songs.resolve_default_soundfont", lambda: None)

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["fallback_reason"] == "soundfont_not_found"


def test_render_fallback_reason_soundfont_file_missing(tmp_path, monkeypatch):
    """soundfont_id 存在但文件缺失 → fallback_reason=soundfont_file_missing。"""
    from packages.music_core.audio.soundfont_models import SoundFontInfo

    sf = SoundFontInfo(
        id="abc123",
        name="Ghost",
        path=str(tmp_path / "ghost.sf2"),
        format="sf2",
        size_bytes=0,
    )
    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.get_project_soundfont",
        lambda _sid: {"soundfont_id": "abc123", "soundfont_name": "Ghost"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: sf)
    monkeypatch.setattr("services.api.routes.songs.resolve_default_soundfont", lambda: None)

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["fallback_reason"] == "soundfont_file_missing"


def test_render_fluidsynth_success_mock(tmp_path, monkeypatch):
    """mock FluidSynth 成功 → renderer=fluidsynth，is_fallback=false，无 fallback warning。"""
    from packages.music_core.audio.soundfont_models import SoundFontInfo

    sf = SoundFontInfo(
        id="fluidsynth-ok",
        name="GeneralUser-GS",
        path=_make_fake_sf2(tmp_path, "GeneralUser-GS.sf2"),
        format="sf2",
        size_bytes=300,
    )

    class FakeResult:
        renderer = "fluidsynth"
        sample_rate = 44100
        duration_seconds = 5.0
        file_size = 12345
        warnings: list[str] = []

    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.detect_fluidsynth",
        lambda: {"available": True, "binary": "fluidsynth", "version": "2.3.0", "error": None},
    )
    monkeypatch.setattr(
        "services.api.routes.songs.get_project_soundfont",
        lambda _sid: {"soundfont_id": "fluidsynth-ok", "soundfont_name": "GeneralUser-GS"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: sf)
    monkeypatch.setattr(
        "packages.renderer.fluidsynth_renderer.FluidSynthRenderer.render_wav",
        lambda *a, **k: FakeResult(),
    )

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["renderer"] == "fluidsynth"
    assert meta["is_fallback"] is False
    assert meta["fallback_reason"] is None
    assert meta["soundfont_name"] == "GeneralUser-GS"
    codes = [w["code"] for w in meta["renderer_warnings"]]
    assert "FALLBACK_RENDERER_QUALITY" not in codes


def test_render_fluidsynth_failed_fallback(tmp_path, monkeypatch):
    """FluidSynth 抛错 → fallback_reason=fluidsynth_render_failed。"""
    from packages.music_core.audio.soundfont_models import SoundFontInfo

    sf = SoundFontInfo(
        id="fail-id",
        name="Broken",
        path=_make_fake_sf2(tmp_path, "Broken.sf2"),
        format="sf2",
        size_bytes=300,
    )

    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.detect_fluidsynth",
        lambda: {"available": True, "binary": "fluidsynth", "version": "2.3.0", "error": None},
    )
    monkeypatch.setattr(
        "services.api.routes.songs.get_project_soundfont",
        lambda _sid: {"soundfont_id": "fail-id", "soundfont_name": "Broken"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: sf)

    def boom(*a, **k):
        raise RuntimeError("fluidsynth exit=1")

    monkeypatch.setattr("packages.renderer.fluidsynth_renderer.FluidSynthRenderer.render_wav", boom)

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["renderer"] == "fallback"
    assert meta["is_fallback"] is True
    assert meta["fallback_reason"] == "fluidsynth_render_failed"
    codes = [w["code"] for w in meta["renderer_warnings"]]
    assert "FALLBACK_RENDERER_QUALITY" in codes
    assert "FALLBACK_REASON" in codes


def test_diagnostics_api(tmp_path, monkeypatch):
    """诊断 API 返回 soundfonts / fluidsynth / renderer_backends。"""
    from packages.music_core.audio.soundfont_models import SoundFontInfo

    sf = SoundFontInfo(
        id="diag-1",
        name="GeneralUser-GS",
        path=_make_fake_sf2(tmp_path, "GeneralUser-GS.sf2"),
        format="sf2",
        size_bytes=300,
    )
    monkeypatch.setattr("services.api.routes.soundfonts.list_soundfonts", lambda: [sf])
    monkeypatch.setattr(
        "services.api.routes.soundfonts.detect_fluidsynth",
        lambda: {
            "available": False,
            "binary": None,
            "version": None,
            "version_arg": None,
            "version_check_errors": [
                {"arg": "-V", "returncode": 1, "stderr": "Unknown switch '-'"},
                {"arg": "--version", "returncode": 1, "stderr": "Unknown switch '-'"},
            ],
            "error": "fluidsynth not found in PATH",
        },
    )

    resp = client.get("/api/v1/soundfonts/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["soundfonts_found"] == 1
    assert data["soundfonts"][0]["name"] == "GeneralUser-GS"
    assert data["soundfonts"][0]["valid"] is True
    assert data["fluidsynth"]["available"] is False
    assert data["fluidsynth"]["version_arg"] is None
    assert len(data["fluidsynth"]["version_check_errors"]) == 2
    assert data["fluidsynth"]["version_check_errors"][0]["arg"] == "-V"
    assert data["renderer_backends"]["fluidsynth"] is False
    assert data["renderer_backends"]["fallback"] is True


def test_diagnostics_api_fluidsynth_available(monkeypatch):
    """诊断 API 在 -V 成功时显示 version_arg=-V 与 available=true。"""
    monkeypatch.setattr("services.api.routes.soundfonts.list_soundfonts", lambda: [])
    monkeypatch.setattr(
        "services.api.routes.soundfonts.detect_fluidsynth",
        lambda: {
            "available": True,
            "binary": "C:/ProgramData/chocolatey/bin/fluidsynth.exe",
            "version": "FluidSynth runtime version 2.4.7",
            "version_arg": "-V",
            "version_check_errors": [
                {"arg": "--version", "returncode": 1, "stderr": "Unknown switch '-'"}
            ],
            "error": None,
        },
    )

    resp = client.get("/api/v1/soundfonts/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fluidsynth"]["available"] is True
    assert data["fluidsynth"]["version_arg"] == "-V"
    assert data["fluidsynth"]["version"] == "FluidSynth runtime version 2.4.7"
    assert data["renderer_backends"]["fluidsynth"] is True


def test_async_render_task_returns_same_metadata(tmp_path, monkeypatch):
    """异步 render-audio 任务返回与同步一致的 renderer metadata。"""
    import time

    from packages.music_core.audio.soundfont_models import SoundFontInfo

    sf = SoundFontInfo(
        id="async-ok",
        name="GeneralUser-GS",
        path=_make_fake_sf2(tmp_path, "GeneralUser-GS.sf2"),
        format="sf2",
        size_bytes=300,
    )

    class FakeResult:
        renderer = "fluidsynth"
        sample_rate = 44100
        duration_seconds = 5.0
        file_size = 12345
        warnings: list[str] = []

    _auto_renderer(monkeypatch)
    monkeypatch.setattr(
        "services.api.routes.songs.detect_fluidsynth",
        lambda: {"available": True, "binary": "fluidsynth", "version": "2.3.0", "error": None},
    )
    monkeypatch.setattr(
        "services.api.routes.songs.get_project_soundfont",
        lambda _sid: {"soundfont_id": "async-ok", "soundfont_name": "GeneralUser-GS"},
    )
    monkeypatch.setattr("services.api.routes.songs.get_soundfont", lambda _sid: sf)
    monkeypatch.setattr(
        "packages.renderer.fluidsynth_renderer.FluidSynthRenderer.render_wav",
        lambda *a, **k: FakeResult(),
    )

    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    task = client.post(f"/api/v1/songs/{song_id}/tasks/render-audio")
    assert task.status_code == 202
    task_id = task.json()["task_id"]

    result = None
    for _ in range(30):
        poll = client.get(f"/api/v1/tasks/{task_id}").json()
        if poll["status"] in ("succeeded", "failed"):
            result = poll
            break
        time.sleep(0.2)
    assert result is not None
    assert result["status"] == "succeeded"
    audio_metadata = result["result"].get("audio_metadata")
    assert audio_metadata is not None
    assert audio_metadata["renderer"] == "fluidsynth"
    assert audio_metadata["is_fallback"] is False
    assert audio_metadata["fallback_reason"] is None
