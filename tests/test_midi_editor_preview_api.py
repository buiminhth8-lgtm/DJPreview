"""T34.7：MIDI Editor scratch preview API（draft/scope/state boundary/cleanup）。"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path

import mido
from fastapi.testclient import TestClient
from mido import Message, MetaMessage, MidiFile, MidiTrack

import services.api.routes.songs as songs_route
import services.api.storage.project_store as store
from packages.renderer.audio_metadata import AudioRenderResult
from services.api.main import app


client = TestClient(app)


def _write_fixture_midi(path: Path) -> Path:
    midi = MidiFile(ticks_per_beat=480)
    meta = MidiTrack()
    meta.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(90)))
    meta.append(MetaMessage("time_signature", numerator=4, denominator=4))
    midi.tracks.append(meta)
    for name, pitch, channel in (("melody", 72, 0), ("bass", 40, 2)):
        track = MidiTrack()
        track.append(MetaMessage("track_name", name=name))
        track.append(Message("note_on", note=pitch, velocity=100, time=0, channel=channel))
        track.append(Message("note_off", note=pitch, velocity=0, time=480, channel=channel))
        midi.tracks.append(track)
    midi.save(str(path))
    return path


def _create_song() -> str:
    response = client.post("/api/v1/songs/generate", json={"prompt": "preview test piece"})
    assert response.status_code == 200
    song_id = response.json()["song_id"]
    with tempfile.TemporaryDirectory() as directory:
        store.save_midi_file(song_id, _write_fixture_midi(Path(directory) / "fixture.mid"))
    return song_id


def _note(note_id: str, pitch: int, channel: int, start: int = 0, duration: int = 480) -> dict:
    return {
        "id": note_id,
        "pitch": pitch,
        "start_tick": start,
        "duration_tick": duration,
        "velocity": 100,
        "channel": channel,
    }


def _fake_renderer(captured: list[dict[str, list[int]]]):
    def render(_song_id: str, midi_path: Path, wav_path: Path) -> AudioRenderResult:
        captured.append(_pitches_by_track(Path(midi_path)))
        with wave.open(str(wav_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(8000)
            output.writeframes(b"\0\0" * 80)
        return AudioRenderResult(
            wav_path=wav_path,
            renderer="test-preview",
            sample_rate=8000,
            duration_seconds=0.01,
            file_size=wav_path.stat().st_size,
            warnings=[],
        )

    return render


def _pitches_by_track(path: Path) -> dict[str, list[int]]:
    midi = MidiFile(str(path))
    result: dict[str, list[int]] = {}
    for track in midi.tracks:
        name = next((msg.name for msg in track if msg.type == "track_name"), None)
        if name:
            result[name] = [msg.note for msg in track if msg.type == "note_on" and msg.velocity > 0]
    return result


def test_current_track_preview_uses_draft_and_silences_other_tracks(monkeypatch):
    song_id = _create_song()
    captured: list[dict[str, list[int]]] = []
    monkeypatch.setattr(songs_route, "_render_editor_preview_for", _fake_renderer(captured))
    response = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={"scope": "current_track", "tracks": [{"track_id": "bass", "notes": [_note("draft", 45, 2)]}]},
    )
    assert response.status_code == 200
    pitches = captured[0]
    assert pitches["bass"] == [45]
    assert pitches["melody"] == []
    client.delete(response.json()["cleanup_url"])


def test_all_tracks_preview_merges_saved_and_draft(monkeypatch):
    song_id = _create_song()
    captured: list[dict[str, list[int]]] = []
    monkeypatch.setattr(songs_route, "_render_editor_preview_for", _fake_renderer(captured))
    response = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={
            "scope": "all_tracks",
            "tracks": [
                {"track_id": "melody", "notes": [_note("saved", 72, 0)]},
                {"track_id": "bass", "notes": [_note("draft", 47, 2)]},
            ],
        },
    )
    assert response.status_code == 200
    assert captured[0] == {"melody": [72], "bass": [47]}
    stream = client.get(response.json()["stream_url"])
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("audio/wav")
    cleanup = client.delete(response.json()["cleanup_url"])
    assert cleanup.json()["cleaned"] is True
    assert client.get(response.json()["stream_url"]).status_code == 404


def test_preview_does_not_change_version_midi_wav_or_renderer_metadata(monkeypatch):
    song_id = _create_song()
    monkeypatch.setattr(songs_route, "_render_editor_preview_for", _fake_renderer([]))
    project_dir = store.get_project_dir(song_id)
    midi_before = (project_dir / "output.mid").read_bytes()
    version_before = store.get_current_version(song_id)
    metadata_before = store.get_audio_metadata(song_id)
    response = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={"scope": "current_track", "tracks": [{"track_id": "bass", "notes": [_note("draft", 48, 2)]}]},
    )
    assert response.status_code == 200
    assert (project_dir / "output.mid").read_bytes() == midi_before
    assert store.get_current_version(song_id) == version_before
    assert store.get_audio_metadata(song_id) == metadata_before
    assert not (project_dir / "output.wav").exists()
    client.delete(response.json()["cleanup_url"])


def test_invalid_scope_track_sets_are_rejected(monkeypatch):
    song_id = _create_song()
    monkeypatch.setattr(songs_route, "_render_editor_preview_for", _fake_renderer([]))
    current = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={
            "scope": "current_track",
            "tracks": [
                {"track_id": "bass", "notes": []},
                {"track_id": "melody", "notes": []},
            ],
        },
    )
    assert current.status_code == 400
    all_missing = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={"scope": "all_tracks", "tracks": [{"track_id": "bass", "notes": []}]},
    )
    assert all_missing.status_code == 400


def test_preview_accepts_3000_notes_without_scheduling_timers(monkeypatch):
    song_id = _create_song()
    monkeypatch.setattr(songs_route, "_render_editor_preview_for", _fake_renderer([]))
    notes = [_note(f"n-{index}", 36 + (index % 24), 2, index * 30, 30) for index in range(3000)]
    response = client.post(
        f"/api/v1/songs/{song_id}/midi/preview",
        json={"scope": "current_track", "tracks": [{"track_id": "bass", "notes": notes}]},
    )
    assert response.status_code == 200
    client.delete(response.json()["cleanup_url"])
