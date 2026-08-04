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
