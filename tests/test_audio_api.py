"""音频渲染 API 集成测试（AUDIO_RENDERER=fallback）。"""

import json

from fastapi.testclient import TestClient

from services.api.dependencies.config import get_settings
from services.api.main import app

client = TestClient(app)


def _create_song(prompt: str = "生成一段忧郁空灵的钢琴配乐") -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": prompt})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_audio_render_stream_download_assets():
    song_id = _create_song()
    assert client.post(f"/api/v1/songs/{song_id}/midi/generate").status_code == 200

    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["audio_file"] == "output.wav"
    assert data["metadata"]["renderer"] == "fallback"
    assert data["metadata"]["duration_seconds"] and data["metadata"]["duration_seconds"] > 0
    assert data["metadata"]["file_size"] > 0

    stream = client.get(f"/api/v1/songs/{song_id}/audio/stream")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("audio/wav")
    assert stream.content[:4] == b"RIFF"

    download = client.get(f"/api/v1/songs/{song_id}/audio/download")
    assert download.status_code == 200
    assert download.content[:4] == b"RIFF"

    assets = client.get(f"/api/v1/songs/{song_id}/assets")
    assert assets.status_code == 200
    payload = assets.json()
    assert payload["has_music_spec"] is True
    assert payload["has_midi"] is True
    assert payload["has_audio"] is True
    assert payload["audio"]["metadata"]["renderer"] == "fallback"


def test_audio_metadata_file_saved():
    """audio_metadata.json 必须正确保存 renderer/sample_rate/duration_seconds/file_size/warnings。"""
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200

    meta_path = get_settings().projects_dir / song_id / "audio_metadata.json"
    assert meta_path.exists()
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    for key in ("renderer", "sample_rate", "duration_seconds", "file_size", "warnings", "generator_version"):
        assert key in metadata, f"metadata 缺少字段 {key}"
    assert metadata["renderer"] == "fallback"
    assert metadata["sample_rate"] > 0
    assert metadata["duration_seconds"] and metadata["duration_seconds"] > 0
    assert metadata["file_size"] > 0
    assert isinstance(metadata["warnings"], list)
    assert metadata["generator_version"] == "stage-3-audio-v0.1"


def test_audio_render_auto_generates_midi():
    """只有 MusicSpec 时，audio/render 应自动先生成 MIDI。"""
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/audio/render")
    assert resp.status_code == 200
    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["has_midi"] is True
    assert assets["has_audio"] is True


def test_audio_endpoints_missing_song_404():
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/songs/{missing}/audio/render").status_code == 404
    assert client.get(f"/api/v1/songs/{missing}/audio/stream").status_code == 404
    assert client.get(f"/api/v1/songs/{missing}/audio/download").status_code == 404
    assert client.get(f"/api/v1/songs/{missing}/assets").status_code == 404


def test_assets_before_render():
    song_id = _create_song()
    client.post(f"/api/v1/songs/{song_id}/midi/generate")
    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["has_midi"] is True
    assert assets["has_audio"] is False
    assert assets["audio"] is None


def test_generate_with_audio_endpoint():
    resp = client.post("/api/v1/songs/generate-with-audio", json={"prompt": "欢快明亮的流行歌"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"]
    assert data["midi"]["midi_file"] == "output.mid"
    assert data["audio"]["audio_file"] == "output.wav"
    assert data["audio"]["metadata"]["renderer"] == "fallback"
