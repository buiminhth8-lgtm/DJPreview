"""局部重生成引擎测试。"""

from packages.music_core.regeneration.regeneration_engine import regenerate_music_spec
from packages.music_core.regeneration.regeneration_models import RegenerationRequest
from packages.music_core.validation.spec_validator import validate_music_spec
from tests.test_harmony_engine import build_spec


def test_section_regen_only_changes_target_section():
    spec = build_spec()
    original_energies = {s.id: s.energy for s in spec.form}
    new_spec, report = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="section", section_id="chorus", variation_strength=0.8, seed_offset=2),
    )
    for section in new_spec.form:
        if section.id == "chorus":
            assert section.energy != original_energies["chorus"]
        else:
            assert section.energy == original_energies[section.id]
    assert any(c["section_id"] == "chorus" for c in report["changes"])
    validate_music_spec(new_spec)


def test_track_regen_only_changes_target_track():
    spec = build_spec()
    original = {t.id: t.velocity for t in spec.tracks}
    new_spec, _ = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="track", track_id="bass", variation_strength=0.8, seed_offset=2),
    )
    for track in new_spec.tracks:
        if track.id == "bass":
            assert track.velocity != original["bass"]
        else:
            assert track.velocity == original[track.id]
    validate_music_spec(new_spec)


def test_keep_harmony_true_preserves_harmony():
    spec = build_spec()
    original_harmony = [h.model_dump() for h in spec.harmony]
    new_spec, _ = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="overall", keep_harmony=True, seed_offset=1),
    )
    assert [h.model_dump() for h in new_spec.harmony] == original_harmony


def test_higher_variation_changes_more():
    spec = build_spec()
    low, _ = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="track", track_id="melody", variation_strength=0.2, seed_offset=2),
    )
    high, _ = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="track", track_id="melody", variation_strength=1.0, seed_offset=2),
    )
    low_vel = next(t for t in low.tracks if t.id == "melody").velocity
    high_vel = next(t for t in high.tracks if t.id == "melody").velocity
    assert abs(high_vel - spec.tracks[0].velocity) >= abs(low_vel - spec.tracks[0].velocity)


def test_overall_regen_changes_seed_and_valid():
    spec = build_spec()
    new_spec, report = regenerate_music_spec(
        spec,
        RegenerationRequest(scope="overall", seed_offset=5),
    )
    assert new_spec.seed == spec.seed + 5
    assert any(c["field"] == "seed" for c in report["changes"])
    validate_music_spec(new_spec)
