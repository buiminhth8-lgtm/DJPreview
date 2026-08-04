"""参考 MIDI API 测试。"""

import mido

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def _reference_midi(tmp_path):
    midi = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(90)))
    track.append(mido.Message("note_on", note=60, velocity=90, time=0, channel=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=480, channel=0))
    track.append(mido.MetaMessage("end_of_track"))
    midi.tracks.append(track)
    path = tmp_path / "ref.mid"
    midi.save(str(path))
    return path


def test_analyze_reference_api(tmp_path):
    path = _reference_midi(tmp_path)
    with open(path, "rb") as f:
        resp = client.post("/api/v1/reference/analyze", files={"file": ("ref.mid", f, "audio/midi")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["note_count"] > 0
    assert data["bpm"] == 90


def test_analyze_reference_wrong_extension(tmp_path):
    resp = client.post(
        "/api/v1/reference/analyze",
        files={"file": ("ref.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_generate_from_reference(tmp_path):
    path = _reference_midi(tmp_path)
    with open(path, "rb") as f:
        resp = client.post(
            "/api/v1/songs/generate-from-reference",
            data={"prompt": "生成一段类似能量变化但旋律不同的配乐", "style_template_id": "cinematic_piano"},
            files={"file": ("ref.mid", f, "audio/midi")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["song_id"]
    assert data["music_spec"]["tempo"]["bpm"] == 90
    assert data["style_template"]["id"] == "cinematic_piano"
