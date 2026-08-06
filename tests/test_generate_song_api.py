"""歌曲生成 / 查询 API 集成测试。"""

import json

from fastapi.testclient import TestClient

from packages.llm.factory import get_llm_provider
from packages.llm.mock_provider import MockProvider
from services.api.main import app

client = TestClient(app)


def test_default_provider_is_mock():
    """未设置 LLM_PROVIDER 时默认 mock，确保回归不依赖外部服务。"""
    assert isinstance(get_llm_provider(), MockProvider)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["request_id"]


def test_generate_and_get_song():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    data = resp.json()
    assert "song_id" in data
    assert data["music_spec"]["version"] == "0.1"
    assert data["music_spec"]["tempo"]["bpm"] == 72
    assert data["music_spec"]["tonality"]["key"] == "D"
    assert len(data["music_spec"]["tracks"]) >= 5

    song_id = data["song_id"]
    resp2 = client.get(f"/api/v1/songs/{song_id}")
    assert resp2.status_code == 200
    got = resp2.json()
    assert got["song_id"] == song_id
    assert got["music_spec"]["prompt"] == "生成一段忧郁空灵的钢琴配乐"


def test_empty_prompt_rejected():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "   "})
    assert resp.status_code == 422


def test_get_missing_song_returns_404():
    resp = client.get("/api/v1/songs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_generated_harmony_parseable():
    """T19：MockProvider 生成的 harmony 全部可解析。"""
    from packages.music_core.theory.chords import is_valid_chord_symbol

    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["music_spec"]["harmony"]
    for section in data["music_spec"]["harmony"]:
        assert section["progression"]
        assert all(is_valid_chord_symbol(c) for c in section["progression"])


def test_generated_song_has_drums_track():
    """T20：MockProvider 默认生成包含 drums track。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    tracks = resp.json()["music_spec"]["tracks"]
    assert any(t["role"] == "drums" for t in tracks)


def test_generated_song_has_bass_track():
    """T21：MockProvider 默认生成包含 bass track。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    tracks = resp.json()["music_spec"]["tracks"]
    assert any(t["role"] == "bass" for t in tracks)


def test_generate_response_has_debug_metadata():
    """T35：生成响应包含 request_id / debug / warnings。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "生成一段忧郁空灵的钢琴配乐"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"]
    assert data["debug"]["provider"] == "mock"
    assert data["debug"]["request_id"] == data["request_id"]
    assert "llm_duration_ms" in data["debug"]
    assert "validation_warning_count" in data["debug"]
    assert isinstance(data["warnings"], list)
    # debug 元数据不应包含 api key
    assert "api_key" not in json.dumps(data["debug"]).lower()


def test_cinematic_prompt_has_strings_and_pad():
    """T22：cinematic / chinese cinematic prompt 生成 strings 与 pad。"""
    resp = client.post("/api/v1/songs/generate", json={"prompt": "cinematic 电影配乐"})
    assert resp.status_code == 200
    roles = {t["role"] for t in resp.json()["music_spec"]["tracks"]}
    assert "strings" in roles
    assert "pad" in roles

    resp2 = client.post("/api/v1/songs/generate", json={"prompt": "带有中国风韵味的旋律"})
    assert resp2.status_code == 200
    roles2 = {t["role"] for t in resp2.json()["music_spec"]["tracks"]}
    assert "strings" in roles2
    assert "pad" in roles2


def test_generate_normalizes_llm_instrument_aliases(monkeypatch):
    """T36：生成链路中 brass / distorted guitar 别名被归一化。"""
    import httpx

    from packages.music_core.planner import music_planner
    from packages.llm.openai_compatible_provider import OpenAICompatibleProvider
    from tests.test_harmony_engine import build_spec

    spec_dict = build_spec().model_dump(mode="json")
    # 模拟 Gemini 输出 brass / electric_guitar_distorted
    spec_dict["tracks"] = [
        *[t for t in spec_dict["tracks"] if t["role"] not in ("melody", "harmony")],
        {"id": "brass_epic", "role": "melody", "instrument": "brass", "pattern": "sustained", "register": "mid-high", "velocity": 110},
        {"id": "dist_guitar", "role": "harmony", "instrument": "electric_guitar_distorted", "pattern": "power_chords", "register": "mid", "velocity": 105},
    ]

    def fake_provider(*args, **kwargs):
        return OpenAICompatibleProvider(
            api_key="sk-test",
            base_url="http://localhost:9999/v1",
            model="gemini-3.5-flash",
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    200,
                    json={"choices": [{"message": {"role": "assistant", "content": __import__("json").dumps(spec_dict)}}]},
                )
            ),
        )

    monkeypatch.setattr(music_planner, "get_llm_provider", fake_provider)
    from packages.music_core.planner.music_planner import generate_music_spec_from_prompt

    spec = generate_music_spec_from_prompt("游戏 Boss 战音乐")
    instruments = {t.instrument for t in spec.tracks}
    assert "brass_section" in instruments
    assert "distortion_guitar" in instruments
    assert "brass" not in instruments
    assert "electric_guitar_distorted" not in instruments
