"""MixEngine 测试。"""

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.mix.mix_engine import (
    apply_mix_to_composition,
    create_default_mix_spec,
    sync_mix_spec_with_music_spec,
    update_track_mix,
)
from packages.music_core.mix.mix_models import TrackMixSpec
from tests.test_harmony_engine import build_spec


def _composition():
    return compose_music(build_spec())


def test_create_default_mix_spec():
    spec = build_spec()
    mix = create_default_mix_spec(spec, song_id="s1", version_id="v1")
    assert {t.track_id for t in mix.tracks} == {t.id for t in spec.tracks}
    assert mix.song_id == "s1"


def test_sync_adds_and_removes_tracks():
    spec = build_spec()
    mix = create_default_mix_spec(spec)
    mix = update_track_mix(mix, "piano", {"volume": 0.5})
    # 删除 drums，新增 extra
    spec.tracks = [t for t in spec.tracks if t.id != "drums"]
    from services.api.schemas.music_spec import TrackSpec

    spec.tracks.append(TrackSpec(id="extra", role="pad", instrument="strings", velocity=70))
    synced = sync_mix_spec_with_music_spec(mix, spec)
    ids = {t.track_id for t in synced.tracks}
    assert "drums" not in ids
    assert "extra" in ids
    assert next(t for t in synced.tracks if t.track_id == "piano").volume == 0.5


def test_mute_removes_notes():
    composition = _composition()
    mix = create_default_mix_spec(build_spec())
    mix = update_track_mix(mix, "drums", {"mute": True})
    result = apply_mix_to_composition(composition, mix)
    drums = next(t for t in result.tracks if t.role == "drums")
    assert drums.notes == []
    others = [t for t in result.tracks if t.role != "drums"]
    assert all(t.notes for t in others)


def test_solo_keeps_only_solo_track():
    composition = _composition()
    mix = create_default_mix_spec(build_spec())
    mix = update_track_mix(mix, "bass", {"solo": True})
    result = apply_mix_to_composition(composition, mix)
    non_empty = [t for t in result.tracks if t.notes]
    assert [t.role for t in non_empty] == ["bass"]


def test_volume_affects_velocity():
    composition = _composition()
    spec = build_spec()
    mix = create_default_mix_spec(spec)
    mix = mix.model_copy(update={"master_volume": 0.5})
    result = apply_mix_to_composition(composition, mix)
    original = compose_music(spec)
    for track in result.tracks:
        orig_track = next(t for t in original.tracks if t.track_id == track.track_id)
        if orig_track.notes:
            assert track.notes[0].velocity < orig_track.notes[0].velocity


def test_pan_set_on_track_events():
    composition = _composition()
    mix = create_default_mix_spec(build_spec())
    mix = update_track_mix(mix, "piano", {"pan": -1.0})
    result = apply_mix_to_composition(composition, mix)
    piano = next(t for t in result.tracks if t.track_id == "piano")
    assert piano.pan == 0
    mix2 = update_track_mix(mix, "piano", {"pan": 1.0})
    result2 = apply_mix_to_composition(composition, mix2)
    piano2 = next(t for t in result2.tracks if t.track_id == "piano")
    assert piano2.pan == 127


def test_all_muted_keeps_one_track_with_warning():
    composition = _composition()
    mix = create_default_mix_spec(build_spec())
    mix = mix.model_copy(
        update={"tracks": [TrackMixSpec(track_id=t.track_id, mute=True) for t in mix.tracks]}
    )
    result = apply_mix_to_composition(composition, mix)
    non_empty = [t for t in result.tracks if t.notes]
    assert len(non_empty) == 1
    assert result.warnings


def test_apply_does_not_mutate_original():
    composition = _composition()
    mix = create_default_mix_spec(build_spec())
    mix = update_track_mix(mix, "piano", {"mute": True})
    before = [len(t.notes) for t in composition.tracks]
    apply_mix_to_composition(composition, mix)
    after = [len(t.notes) for t in composition.tracks]
    assert before == after
