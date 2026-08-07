"""T07：编辑接口 auto_render 测试。"""

from fastapi.testclient import TestClient

from services.api.dependencies.config import get_settings
from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def _version_count(song_id: str) -> int:
    return len(client.get(f"/api/v1/songs/{song_id}/versions").json()["versions"])


def test_edit_old_request_compat():
    """旧请求（不带 auto_render）行为不变：默认 true 并渲染音频。"""
    song_id = _create_song()
    before = _version_count(song_id)
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "副歌更亮一点"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_render"] is True
    assert data["audio_rendered"] is True
    assert _version_count(song_id) == before + 1
    assert data["assets"]["has_midi"] is True
    assert data["assets"]["has_audio"] is True


def test_edit_auto_render_true():
    song_id = _create_song()
    resp = client.post(
        f"/api/v1/songs/{song_id}/edit",
        json={"instruction": "加入弦乐", "auto_render": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_render"] is True
    assert data["audio_rendered"] is True
    assert data["assets"]["has_midi"] is True
    assert data["assets"]["has_audio"] is True


def test_edit_auto_render_false_skips_audio(monkeypatch):
    """auto_render=false 时不调用渲染器（monkeypatch 触发即抛异常）。"""

    def boom(*args, **kwargs):
        raise AssertionError("renderer should not be called when auto_render=false")

    monkeypatch.setattr("services.api.routes.songs._render_audio_for", boom)

    song_id = _create_song()
    before = _version_count(song_id)
    resp = client.post(
        f"/api/v1/songs/{song_id}/edit",
        json={"instruction": "副歌更亮一点", "auto_render": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auto_render"] is False
    assert data["audio_rendered"] is False
    assert _version_count(song_id) == before + 1
    assert data["assets"]["has_midi"] is True
    assert data["assets"]["has_audio"] is False


def test_edit_auto_render_false_keeps_existing_wav():
    """auto_render=false 不覆盖已有 output.wav。"""
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/audio/render")
    wav_path = get_settings().projects_dir / song_id / "output.wav"
    before = wav_path.read_bytes()
    assert len(before) > 0

    resp = client.post(
        f"/api/v1/songs/{song_id}/edit",
        json={"instruction": "副歌更亮一点", "auto_render": False},
    )
    assert resp.status_code == 200
    assert resp.json()["audio_rendered"] is False
    assert resp.json()["assets"]["has_audio"] is True  # 旧音频仍在
    assert wav_path.read_bytes() == before


def test_edit_missing_song_404():
    resp = client.post(
        "/api/v1/songs/00000000-0000-0000-0000-000000000000/edit",
        json={"instruction": "更快"},
    )
    assert resp.status_code == 404
