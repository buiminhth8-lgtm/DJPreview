"""T15：Evaluation API render_audio 行为测试。"""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _run(payload=None):
    return client.post("/api/v1/evaluation/run", json=payload or {})


def test_evaluation_api_defaults_to_no_audio():
    resp = _run({"case_ids": ["cinematic_piano"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["render_audio"] is False
    assert data["audio_rendered_cases"] == 0
    assert data["audio_failed_cases"] == 0
    assert data["results"][0]["audio_rendered"] is False
    assert data["results"][0]["audio_path"] is None


def test_evaluation_api_render_audio_true():
    resp = _run({"case_ids": ["cinematic_piano"], "render_audio": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["render_audio"] is True
    assert data["audio_rendered_cases"] >= 1
    result = data["results"][0]
    assert result["audio_rendered"] is True
    assert result["audio_path"]
    assert result["renderer"] == "fallback"
    assert result["render_error"] is None
