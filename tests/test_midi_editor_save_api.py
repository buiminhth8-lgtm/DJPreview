"""T34.6：MIDI Editor Save API 测试（写回 + 版本 + 409 + validation）。"""

import tempfile
from pathlib import Path

import mido
from fastapi.testclient import TestClient
from mido import Message, MetaMessage, MidiFile, MidiTrack

from services.api.main import app
import services.api.storage.project_store as store

client = TestClient(app)

DRUM_CHANNEL = 9


def _write_fixture_midi(path: Path) -> Path:
    tpb = 480
    midi = MidiFile(ticks_per_beat=tpb)
    meta = MidiTrack()
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(120)))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4))
    meta.append(MetaMessage("end_of_track"))
    midi.tracks.append(meta)

    mel = MidiTrack()
    mel.append(MetaMessage("track_name", name="melody"))
    mel.append(Message("note_on", note=72, velocity=100, time=0, channel=0))
    mel.append(Message("note_off", note=72, velocity=0, time=480, channel=0))
    mel.append(MetaMessage("end_of_track"))
    midi.tracks.append(mel)

    bass = MidiTrack()
    bass.append(MetaMessage("track_name", name="bass"))
    bass.append(Message("program_change", program=33, time=0, channel=2))
    bass.append(Message("note_on", note=40, velocity=110, time=0, channel=2))
    bass.append(Message("note_off", note=40, velocity=0, time=480, channel=2))
    bass.append(MetaMessage("end_of_track"))
    midi.tracks.append(bass)

    midi.save(str(path))
    return path


def _create_song() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "save test piece"})
    assert resp.status_code == 200
    song_id = resp.json()["song_id"]
    with tempfile.TemporaryDirectory() as d:
        p = _write_fixture_midi(Path(d) / "fixture.mid")
        store.save_midi_file(song_id, p)
    return song_id


def _edit_payload(track_id="bass", notes=None, base_version_id=None):
    if notes is None:
        notes = [
            {"id": "x1", "pitch": 41, "start_tick": 0, "duration_tick": 480, "velocity": 100, "channel": 2},
            {"id": "x2", "pitch": 43, "start_tick": 480, "duration_tick": 240, "velocity": 90, "channel": 2},
        ]
    return {"track_id": track_id, "base_version_id": base_version_id, "notes": notes}


def test_save_creates_new_version():
    song_id = _create_song()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    base = doc["version_id"]
    resp = client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload(base_version_id=base))
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_id"] != base
    # 新版本可读回，bass notes 已替换为编辑结果
    doc2 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    bass2 = next(t for t in doc2["tracks"] if t["id"] == "bass")
    pitches = sorted(n["pitch"] for n in bass2["notes"])
    assert pitches == [41, 43]


def test_save_preserves_other_tracks():
    song_id = _create_song()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    base = doc["version_id"]
    resp = client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload(base_version_id=base))
    assert resp.status_code == 200
    doc2 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    melody2 = next(t for t in doc2["tracks"] if t["id"] == "melody")
    assert [n["pitch"] for n in melody2["notes"]] == [72]


def test_save_version_conflict_409():
    song_id = _create_song()
    # base = v1，但先生成另一个版本让 current 变化
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    base = doc["version_id"]
    client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload(base_version_id=base))
    # 现在 current 已变，再用旧 base 保存 → 409
    resp = client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload(base_version_id=base))
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "VERSION_CONFLICT"


def test_save_unknown_track_400():
    song_id = _create_song()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    resp = client.post(
        f"/api/v1/songs/{song_id}/midi/edit",
        json=_edit_payload(track_id="nope", base_version_id=doc["version_id"]),
    )
    assert resp.status_code == 400


def test_save_missing_midi_404():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "spec only"})
    song_id = resp.json()["song_id"]
    resp2 = client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload())
    assert resp2.status_code == 404


def test_save_validation_bad_note():
    song_id = _create_song()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    bad = _edit_payload(base_version_id=doc["version_id"])
    bad["notes"][0]["pitch"] = 200  # > 127
    resp = client.post(f"/api/v1/songs/{song_id}/midi/edit", json=bad)
    assert resp.status_code == 422


def test_save_does_not_render_wav_or_change_audio():
    song_id = _create_song()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    client.post(f"/api/v1/songs/{song_id}/midi/edit", json=_edit_payload(base_version_id=doc["version_id"]))
    assets = client.get(f"/api/v1/songs/{song_id}/assets").json()
    assert assets["has_audio"] is False  # 未自动渲染 WAV
