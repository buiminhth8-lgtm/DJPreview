"""MixSpec / TrackMixSpec 模型测试。"""

import pytest
from pydantic import ValidationError

from packages.music_core.mix.mix_models import MixSpec, TrackMixSpec


def test_track_mix_defaults():
    track = TrackMixSpec(track_id="piano")
    assert track.volume == 1.0
    assert track.pan == 0.0
    assert track.mute is False
    assert track.solo is False
    assert track.enabled is True
    assert track.velocity_scale == 1.0


def test_volume_out_of_range_fails():
    with pytest.raises(ValidationError):
        TrackMixSpec(track_id="piano", volume=2.0)


def test_pan_out_of_range_fails():
    with pytest.raises(ValidationError):
        TrackMixSpec(track_id="piano", pan=1.5)


def test_mix_spec_multiple_tracks():
    mix = MixSpec(
        song_id="s1",
        tracks=[
            TrackMixSpec(track_id="melody"),
            TrackMixSpec(track_id="bass", volume=0.8, pan=-0.5),
            TrackMixSpec(track_id="drums", mute=True),
        ],
    )
    assert len(mix.tracks) == 3
    assert mix.version == "0.1"
    assert mix.master_volume == 1.0
