"""第四阶段：编辑引擎与 diff 测试。"""

import pytest

from packages.llm.mock_provider import MockProvider
from packages.music_core.editing.diff import diff_music_specs
from packages.music_core.editing.edit_engine import apply_music_edit
from packages.music_core.validation.spec_validator import validate_music_spec
from services.api.schemas.music_edit_spec import EditOperation, EditTarget, MusicEditSpec
from tests.test_harmony_engine import build_spec


def _tempo_edit(amount=10.0, preserve=None, target=None):
    return MusicEditSpec(
        instruction="更快",
        target=target or EditTarget(scope="overall"),
        preserve=preserve or [],
        operations=[EditOperation(type="tempo", amount=amount)],
    )


def test_apply_does_not_mutate_original():
    spec = build_spec()
    original_bpm = spec.tempo.bpm
    new = apply_music_edit(spec, _tempo_edit(10.0))
    assert spec.tempo.bpm == original_bpm  # 原始对象未被修改
    assert new is not spec
    assert new.tempo.bpm == original_bpm + 10


def test_preserve_prevents_change():
    spec = build_spec()
    new = apply_music_edit(spec, _tempo_edit(10.0, preserve=["tempo"]))
    assert new.tempo.bpm == spec.tempo.bpm


def test_section_target_only_changes_chorus():
    spec = build_spec()
    original_energy = {s.id: s.energy for s in spec.form}
    edit = MusicEditSpec(
        instruction="副歌更亮",
        target=EditTarget(scope="section", section="chorus"),
        preserve=[],
        operations=[EditOperation(type="energy", amount=0.15)],
    )
    new = apply_music_edit(spec, edit)
    for section in new.form:
        if section.id == "chorus":
            assert section.energy == round(min(1.0, original_energy["chorus"] + 0.15), 3)
        else:
            assert section.energy == original_energy[section.id]
    # 全局字段不变
    assert new.tempo == spec.tempo
    assert new.tonality == spec.tonality
    assert [t.id for t in new.tracks] == [t.id for t in spec.tracks]


def test_section_target_skips_global_ops():
    spec = build_spec()
    edit = MusicEditSpec(
        instruction="副歌更快更亮",
        target=EditTarget(scope="section", section="chorus"),
        preserve=[],
        operations=[
            EditOperation(type="tempo", amount=10.0),
            EditOperation(type="energy", amount=0.1),
        ],
    )
    new = apply_music_edit(spec, edit)
    assert new.tempo.bpm == spec.tempo.bpm  # 全局 tempo 被跳过
    assert new.form[2].energy > spec.form[2].energy


def test_add_instrument():
    spec = build_spec()
    edit = MusicEditSpec(
        instruction="加鼓",
        target=EditTarget(scope="partial"),
        preserve=[],
        operations=[EditOperation(type="add_instrument", value="drums", params={"role": "drums"})],
    )
    new = apply_music_edit(spec, edit)
    assert any(t.instrument == "drums" and t.role == "drums" for t in new.tracks)
    validate_music_spec(new)


def test_add_instrument_section_scoped():
    spec = build_spec()
    edit = MusicEditSpec(
        instruction="副歌加鼓",
        target=EditTarget(scope="section", section="chorus"),
        preserve=[],
        operations=[EditOperation(type="add_instrument", value="drums", params={"role": "drums"})],
    )
    new = apply_music_edit(spec, edit)
    added = [t for t in new.tracks if t.instrument == "drums" and t.role == "drums"]
    # 新增的鼓轨应限定在副歌；原有鼓轨保持全局
    assert any(t.enabled_sections == ["chorus"] for t in added)
    assert any(t.id == "drums" and t.enabled_sections is None for t in new.tracks)


def test_remove_instrument():
    spec = build_spec()
    edit = MusicEditSpec(
        instruction="去掉鼓",
        target=EditTarget(scope="partial"),
        preserve=[],
        operations=[EditOperation(type="remove_instrument", value="drums")],
    )
    new = apply_music_edit(spec, edit)
    assert not any(t.role == "drums" for t in new.tracks)
    assert len(new.tracks) >= 4
    validate_music_spec(new)


def test_change_tempo_via_mock_provider():
    spec = build_spec()
    edit = MockProvider().generate_music_edit("整首更快一点", spec)
    new = apply_music_edit(spec, edit)
    assert new.tempo.bpm == spec.tempo.bpm + 10


def test_chinese_style_via_mock_provider():
    spec = build_spec()
    edit = MockProvider().generate_music_edit("加点中国风", spec)
    new = apply_music_edit(spec, edit)
    assert new.tonality.mode == "pentatonic"
    assert "中国风" in new.style


def test_mock_provider_section_target_energy():
    spec = build_spec()
    edit = MockProvider().generate_music_edit("副歌更亮一点", spec)
    assert edit.target.scope == "section"
    assert edit.target.section == "chorus"
    new = apply_music_edit(spec, edit)
    chorus_old = next(s for s in spec.form if s.id == "chorus").energy
    chorus_new = next(s for s in new.form if s.id == "chorus").energy
    assert chorus_new > chorus_old
    for section in new.form:
        if section.id != "chorus":
            assert section.energy == next(s for s in spec.form if s.id == section.id).energy


def test_edited_spec_always_valid():
    spec = build_spec()
    edits = [
        MockProvider().generate_music_edit("整首更快一点", spec),
        MockProvider().generate_music_edit("加点中国风", spec),
        MockProvider().generate_music_edit("去掉贝斯", spec),
        MockProvider().generate_music_edit("副歌加鼓", spec),
        MockProvider().generate_music_edit("贝斯音量加大", spec),
    ]
    for edit in edits:
        result = apply_music_edit(spec, edit)
        validate_music_spec(result)  # 不抛异常即合法


def test_diff_reflects_changes():
    spec = build_spec()
    new = apply_music_edit(spec, _tempo_edit(10.0))
    changes = diff_music_specs(spec, new)
    fields = {c["field"] for c in changes}
    assert "tempo.bpm" in fields
    assert "tempo.feel" in fields
    tempo_change = next(c for c in changes if c["field"] == "tempo.bpm")
    assert tempo_change["old"] == spec.tempo.bpm
    assert tempo_change["new"] == new.tempo.bpm


def test_diff_reflects_track_changes():
    spec = build_spec()
    edit = MusicEditSpec(
        instruction="去掉鼓",
        target=EditTarget(scope="partial"),
        preserve=[],
        operations=[EditOperation(type="remove_instrument", value="drums")],
    )
    new = apply_music_edit(spec, edit)
    changes = diff_music_specs(spec, new)
    assert any(c["field"] == "tracks.removed" and c["old"] == "drums" for c in changes)
