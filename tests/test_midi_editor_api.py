"""T34.1: MIDI editor read API tests (read-only).

Uses program-generated small MIDI fixtures; no real user MIDI committed.
"""

from pathlib import Path

import mido
from fastapi.testclient import TestClient
from mido import Message, MetaMessage, MidiFile, MidiTrack

from services.api.main import app

client = TestClient(app)

DRUM_CHANNEL = 9


def _write_fixture_midi(path: Path) -> Path:
    """Generate small MIDI fixture: melody / bass / drums + overlapping notes + velocity=0."""
    tpb = 480
    midi = MidiFile(ticks_per_beat=tpb)
    meta = MidiTrack()
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(120)))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4))
    meta.append(MetaMessage("end_of_track"))
    midi.tracks.append(meta)

    mel = MidiTrack()
    mel.append(MetaMessage("track_name", name="melody"))
    mel.append(Message("program_change", program=0, time=0, channel=0))
    mel.append(Message("note_on", note=72, velocity=100, time=0, channel=0))
    mel.append(Message("note_off", note=72, velocity=0, time=480, channel=0))
    mel.append(Message("note_on", note=74, velocity=90, time=0, channel=0))
    # note_on velocity=0 acts as note_off
    mel.append(Message("note_on", note=74, velocity=0, time=240, channel=0))
    mel.append(Message("note_on", note=72, velocity=100, time=0, channel=0))
    mel.append(Message("note_off", note=72, velocity=0, time=480, channel=0))
    mel.append(MetaMessage("end_of_track"))
    midi.tracks.append(mel)

    bass = MidiTrack()
    bass.append(MetaMessage("track_name", name="bass"))
    bass.append(Message("program_change", program=33, time=0, channel=2))
    # overlapping same-pitch notes (40)
    bass.append(Message("note_on", note=40, velocity=110, time=0, channel=2))
    bass.append(Message("note_on", note=40, velocity=110, time=120, channel=2))
    bass.append(Message("note_off", note=40, velocity=0, time=480, channel=2))
    bass.append(Message("note_off", note=40, velocity=0, time=600, channel=2))
    bass.append(Message("note_on", note=43, velocity=95, time=0, channel=2))
    bass.append(Message("note_off", note=43, velocity=0, time=360, channel=2))
    bass.append(MetaMessage("end_of_track"))
    midi.tracks.append(bass)

    dr = MidiTrack()
    dr.append(MetaMessage("track_name", name="drums"))
    dr.append(Message("note_on", note=36, velocity=120, time=0, channel=DRUM_CHANNEL))
    dr.append(Message("note_off", note=36, velocity=0, time=240, channel=DRUM_CHANNEL))
    dr.append(Message("note_on", note=38, velocity=115, time=240, channel=DRUM_CHANNEL))
    dr.append(Message("note_off", note=38, velocity=0, time=480, channel=DRUM_CHANNEL))
    dr.append(MetaMessage("end_of_track"))
    midi.tracks.append(dr)

    midi.save(str(path))
    return path


def _create_song_with_midi() -> str:
    import tempfile

    import services.api.storage.project_store as store

    resp = client.post("/api/v1/songs/generate", json={"prompt": "generate a test piece"})
    assert resp.status_code == 200
    song_id = resp.json()["song_id"]
    with tempfile.TemporaryDirectory() as d:
        midi_path = _write_fixture_midi(Path(d) / "fixture.mid")
        store.save_midi_file(song_id, midi_path)
    return song_id


def _create_song_missing_midi() -> str:
    resp = client.post("/api/v1/songs/generate", json={"prompt": "spec only project"})
    assert resp.status_code == 200
    return resp.json()["song_id"]


def test_read_basic_document():
    song_id = _create_song_with_midi()
    resp = client.get(f"/api/v1/songs/{song_id}/midi/editor")
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["song_id"] == song_id
    assert doc["ppq"] == 480
    assert doc["bpm"] == 120
    assert doc["time_signature"] == [4, 4]
    names = {t["name"] for t in doc["tracks"]}
    assert "melody" in names
    assert "bass" in names
    assert "drums" in names
    assert any(t["is_drum"] for t in doc["tracks"])


def test_ppq_preserved():
    import tempfile

    import services.api.storage.project_store as store

    song_id = _create_song_missing_midi()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "x.mid"
        midi = MidiFile(ticks_per_beat=960)
        tr = MidiTrack()
        tr.append(MetaMessage("track_name", name="melody"))
        tr.append(Message("note_on", note=60, velocity=100, time=0, channel=0))
        tr.append(Message("note_off", note=60, velocity=0, time=960, channel=0))
        tr.append(MetaMessage("end_of_track"))
        midi.tracks.append(tr)
        midi.save(str(path))
        store.save_midi_file(song_id, path)
    resp = client.get(f"/api/v1/songs/{song_id}/midi/editor")
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["ppq"] == 960
    note = doc["tracks"][0]["notes"][0]
    assert note["start_tick"] == 0
    assert note["duration_tick"] == 960


def test_track_ids_stable_across_reads():
    song_id = _create_song_with_midi()
    d1 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    d2 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    assert [t["id"] for t in d1["tracks"]] == [t["id"] for t in d2["tracks"]]


def test_note_ids_stable_across_reads():
    song_id = _create_song_with_midi()
    d1 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    d2 = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    for t1, t2 in zip(d1["tracks"], d2["tracks"]):
        assert [n["id"] for n in t1["notes"]] == [n["id"] for n in t2["notes"]]


def test_note_fields_correct():
    song_id = _create_song_with_midi()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    bass = next(t for t in doc["tracks"] if t["name"] == "bass")
    pitches_40 = [n for n in bass["notes"] if n["pitch"] == 40]
    assert len(pitches_40) == 2
    for n in bass["notes"]:
        assert 0 <= n["pitch"] <= 127
        assert n["start_tick"] >= 0
        assert n["duration_tick"] > 0
        assert 1 <= n["velocity"] <= 127
        assert 0 <= n["channel"] <= 15


def test_velocity_zero_treated_as_note_off():
    song_id = _create_song_with_midi()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    melody = next(t for t in doc["tracks"] if t["name"] == "melody")
    note74 = [n for n in melody["notes"] if n["pitch"] == 74]
    assert len(note74) == 1
    assert note74[0]["duration_tick"] == 240


def test_drum_detected():
    song_id = _create_song_with_midi()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    drums = next(t for t in doc["tracks"] if t["name"] == "drums")
    assert drums["is_drum"] is True
    assert drums["channel"] == DRUM_CHANNEL
    for n in drums["notes"]:
        assert n["channel"] == DRUM_CHANNEL


def test_missing_midi_returns_error():
    song_id = _create_song_missing_midi()
    resp = client.get(f"/api/v1/songs/{song_id}/midi/editor")
    assert resp.status_code == 404
    assert "MIDI" in resp.json().get("message", "")


def test_missing_project_404():
    missing = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/songs/{missing}/midi/editor")
    assert resp.status_code == 404


def test_invalid_midi_returns_error():
    import services.api.storage.project_store as store

    song_id = _create_song_missing_midi()
    store.save_midi_file(song_id, b"NOT A MIDI FILE at all")
    resp = client.get(f"/api/v1/songs/{song_id}/midi/editor")
    assert resp.status_code in (400, 422)


def test_overlapping_same_note_fifo():
    song_id = _create_song_with_midi()
    doc = client.get(f"/api/v1/songs/{song_id}/midi/editor").json()
    bass = next(t for t in doc["tracks"] if t["name"] == "bass")
    notes_40 = sorted([n for n in bass["notes"] if n["pitch"] == 40], key=lambda n: n["start_tick"])
    assert len(notes_40) == 2
    assert notes_40[0]["start_tick"] == 0
    assert notes_40[1]["start_tick"] == 120
