"""MusicSpec v0.1 协议校验测试。"""

import pytest
from pydantic import ValidationError

from services.api.schemas.music_spec import (
    HarmonySectionSpec,
    LengthSpec,
    MeterSpec,
    MusicSpec,
    SectionSpec,
    TempoSpec,
    TonalitySpec,
    TrackSpec,
)


def valid_music_spec() -> MusicSpec:
    return MusicSpec(
        version="0.1",
        title="测试曲目",
        seed=123,
        language="zh-CN",
        prompt="生成一段忧郁的钢琴曲",
        tempo=TempoSpec(bpm=72, feel="slow"),
        meter=MeterSpec(numerator=4, denominator=4),
        tonality=TonalitySpec(key="D", mode="minor", scale="d-natural-minor"),
        length=LengthSpec(bars=32),
        style=["pop"],
        mood=["calm"],
        form=[
            SectionSpec(id="intro", name="前奏", start_bar=1, bars=4, energy=0.2),
            SectionSpec(id="verse", name="主歌", start_bar=5, bars=8, energy=0.5),
            SectionSpec(id="chorus", name="副歌", start_bar=13, bars=16, energy=0.9),
            SectionSpec(id="outro", name="尾奏", start_bar=29, bars=4, energy=0.3),
        ],
        harmony=[
            HarmonySectionSpec(section="intro", progression=["Dm"]),
            HarmonySectionSpec(section="verse", progression=["Dm", "Bb", "F", "C"]),
            HarmonySectionSpec(section="chorus", progression=["Dm", "Bb", "F", "C", "Bb", "C"]),
            HarmonySectionSpec(section="outro", progression=["Dm"]),
        ],
        tracks=[
            TrackSpec(id="melody", role="melody", instrument="piano", velocity=100),
            TrackSpec(id="bass", role="bass", instrument="bass", velocity=90),
            TrackSpec(id="drums", role="drums", instrument="drums", velocity=100),
        ],
        notes="测试",
    )


def test_valid_music_spec_passes():
    spec = valid_music_spec()
    assert spec.version == "0.1"
    assert len(spec.form) == 4
    assert len(spec.tracks) == 3


def test_bpm_out_of_range_fails():
    spec = valid_music_spec()
    with pytest.raises(ValidationError):
        MusicSpec(**{**spec.model_dump(), "tempo": {"bpm": 300, "feel": None}})


def test_missing_tracks_fails():
    spec = valid_music_spec()
    with pytest.raises(ValidationError):
        MusicSpec(**{**spec.model_dump(), "tracks": []})


def test_section_beyond_length_fails():
    spec = valid_music_spec()
    bad_form = [SectionSpec(id="outro", name="尾奏", start_bar=29, bars=8, energy=0.3)]
    with pytest.raises(ValidationError):
        MusicSpec(**{**spec.model_dump(), "form": bad_form})
