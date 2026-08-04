"""T09：核心接口 response_model 与 OpenAPI 测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_openapi_available():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/songs/generate" in paths
    assert "/api/v1/songs/{song_id}" in paths


def test_generate_song_response():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "欢快明亮的流行歌"})
    assert resp.status_code == 200
    data = resp.json()
    assert "song_id" in data
    assert "music_spec" in data
    assert data["music_spec"]["tempo"]["bpm"] == 120


def test_get_song_response():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert "music_spec" in data


def test_version_list_response():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/versions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert "versions" in data
    assert data["current_version_id"]


def test_version_detail_response():
    song_id = _create_song()
    versions = client.get(f"/api/v1/songs/{song_id}/versions").json()["versions"]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{versions[0]['version_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["version_id"] == versions[0]["version_id"]
    assert "metadata" in data
    assert "music_spec" in data
    assert "assets" in data


def test_version_diff_response():
    song_id = _create_song()
    versions = client.get(f"/api/v1/songs/{song_id}/versions").json()["versions"]
    resp = client.get(f"/api/v1/songs/{song_id}/versions/{versions[0]['version_id']}/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert data["version_id"] == versions[0]["version_id"]
    assert "diff" in data
    assert "metadata" in data


def test_edit_response_has_t07_fields():
    song_id = _create_song()
    resp = client.post(f"/api/v1/songs/{song_id}/edit", json={"instruction": "副歌更亮一点"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert "music_spec" in data
    assert data["auto_render"] is True
    assert data["audio_rendered"] is True


def test_t08_error_response_not_broken():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "PROJECT_NOT_FOUND"
    assert body["message"]
    assert isinstance(body["details"], dict)


def test_piano_roll_response_model():
    song_id = _create_song()
    resp = client.get(f"/api/v1/songs/{song_id}/piano-roll")
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"] == song_id
    assert "tracks" in data
    assert "sections" in data
    assert "ticks_per_beat" in data


def test_evaluation_cases_response_model():
    resp = client.get("/api/v1/evaluation/cases")
    assert resp.status_code == 200
    cases = resp.json()
    assert isinstance(cases, list)
    assert len(cases) >= 8
    assert all("id" in c and "prompt" in c for c in cases)


def test_evaluation_run_response_model_has_audio_fields():
    """T15：evaluation/run 响应包含 render_audio 语义字段。"""
    resp = client.post("/api/v1/evaluation/run", json={"case_ids": ["cinematic_piano"]})
    assert resp.status_code == 200
    data = resp.json()
    for key in ("run_id", "render_audio", "audio_rendered_cases", "audio_failed_cases", "failed_cases"):
        assert key in data
    result = data["results"][0]
    for key in ("render_audio", "audio_rendered", "audio_path", "audio_duration_seconds", "renderer", "render_error"):
        assert key in result
