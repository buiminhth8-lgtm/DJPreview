"""总作曲器测试。"""

from tests.test_harmony_engine import build_spec

from packages.music_core.composer.events import CompositionResult
from packages.music_core.composer.music_composer import compose_music


def _flatten(result: CompositionResult) -> dict[str, list[tuple]]:
    return {
        t.role: [(n.pitch, n.start_beat, n.duration_beats, n.velocity) for n in t.notes]
        for t in result.tracks
    }


def test_compose_returns_composition_result():
    result = compose_music(build_spec())
    assert isinstance(result, CompositionResult)
    assert result.total_bars == 32
    assert result.bpm == 72


def test_has_melody_harmony_bass_drums():
    result = compose_music(build_spec())
    roles = {t.role for t in result.tracks}
    assert {"melody", "harmony", "bass", "drums"} <= roles


def test_non_empty_tracks_have_notes():
    result = compose_music(build_spec())
    for track in result.tracks:
        if track.role in ("melody", "harmony", "bass", "drums", "pad"):
            assert len(track.notes) > 0


def test_same_seed_reproducible():
    r1 = compose_music(build_spec(seed=42))
    r2 = compose_music(build_spec(seed=42))
    assert _flatten(r1) == _flatten(r2)


def test_different_seed_may_differ():
    r1 = compose_music(build_spec(seed=1))
    r2 = compose_music(build_spec(seed=2))
    melody1 = _flatten(r1).get("melody", [])
    melody2 = _flatten(r2).get("melody", [])
    assert melody1 != melody2


def test_melody_notes_valid_and_reasonable_count():
    """T18：旋律音符数量合理、无负 duration / 越界 pitch / 非法 velocity。"""
    result = compose_music(build_spec())
    melody = next(t for t in result.tracks if t.role == "melody")
    assert 16 <= len(melody.notes) <= 256
    assert all(n.duration_beats > 0 for n in melody.notes)
    assert all(n.start_beat >= 0 for n in melody.notes)
    assert all(0 <= n.pitch <= 127 for n in melody.notes)
    assert all(1 <= n.velocity <= 127 for n in melody.notes)


def test_composer_keeps_bass_drums_and_harmony():
    """T18：旋律增强不破坏 bass / drums / harmony。"""
    result = compose_music(build_spec())
    by_role = {t.role: t for t in result.tracks}
    for role in ("bass", "drums", "harmony"):
        assert by_role[role].notes
        assert all(n.duration_beats > 0 for n in by_role[role].notes)


def test_drum_events_valid():
    """T20：鼓组事件 velocity / pitch / time 合法。"""
    result = compose_music(build_spec())
    drums = next(t for t in result.tracks if t.role == "drums")
    assert drums.notes
    assert all(1 <= n.velocity <= 127 for n in drums.notes)
    assert all(0 <= n.pitch <= 127 for n in drums.notes)
    assert all(n.start_beat >= 0 and n.duration_beats > 0 for n in drums.notes)
    assert all(n.channel == 9 and n.is_drum for n in drums.notes)


def test_bass_events_valid():
    """T21：贝斯事件 pitch / velocity / duration 合法。"""
    result = compose_music(build_spec())
    bass = next(t for t in result.tracks if t.role == "bass")
    assert bass.notes
    assert all(1 <= n.velocity <= 127 for n in bass.notes)
    assert all(0 <= n.pitch <= 127 for n in bass.notes)
    assert all(n.start_beat >= 0 and n.duration_beats > 0 for n in bass.notes)
    assert all(n.channel != 9 for n in bass.notes)


def test_background_layers_valid():
    """T22：pad / strings 背景层事件合法。"""
    result = compose_music(build_spec())
    by_role = {t.role: t for t in result.tracks}
    for role in ("pad", "strings"):
        track = by_role.get(role)
        if track is None:
            continue
        assert track.notes
        assert all(n.duration_beats > 0 for n in track.notes)
        assert all(1 <= n.velocity <= 127 for n in track.notes)
        assert all(0 <= n.pitch <= 127 for n in track.notes)
