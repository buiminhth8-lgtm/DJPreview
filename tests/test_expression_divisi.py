"""T33：表达自动化（CC7/CC11）与弦乐 divisi 分部测试。"""

import mido

from packages.music_core.composer.expression import build_volume_curve
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_writer import write_midi
from services.api.schemas.music_spec import TrackSpec
from tests.test_harmony_engine import build_spec


def _spec_with_strings():
    spec = build_spec()
    spec.tracks = spec.tracks + [
        TrackSpec(id="strings", role="strings", instrument="string_ensemble_1", velocity=70)
    ]
    return spec


def test_volume_curve_reflects_section_energy():
    spec = build_spec()
    curve = build_volume_curve(spec)
    by_beat = {beat: value for beat, value in curve}
    # intro (bar 1, energy 0.2) < chorus (bar 13, energy 0.9)
    assert by_beat[0] < by_beat[(13 - 1) * 4]


def test_strings_divisi_two_channels_with_cc():
    spec = _spec_with_strings()
    composition = compose_music(spec)
    divisi = [t for t in composition.tracks if t.track_id.startswith("strings_")]
    assert len(divisi) == 2
    assert divisi[0].channel != divisi[1].channel
    assert divisi[0].pan is not None and divisi[1].pan is not None
    assert divisi[0].cc_curve and divisi[1].cc_curve
    assert divisi[0].cc11 is not None and divisi[1].cc11 is not None
    assert all(n.channel in (divisi[0].channel, divisi[1].channel) for t in divisi for n in t.notes)


def test_midi_file_contains_cc7_cc11_on_strings_channels(tmp_path):
    spec = _spec_with_strings()
    composition = compose_music(spec)
    divisi = [t for t in composition.tracks if t.track_id.startswith("strings_")]
    channels = {t.channel for t in divisi}

    output = write_midi(composition, tmp_path / "expr.mid")
    midi = mido.MidiFile(str(output))
    cc7_channels: set[int] = set()
    cc11_channels: set[int] = set()
    for track in midi.tracks:
        for msg in track:
            if msg.type == "control_change" and msg.control == 7:
                cc7_channels.add(msg.channel)
            if msg.type == "control_change" and msg.control == 11:
                cc11_channels.add(msg.channel)
    assert channels <= cc7_channels
    assert channels <= cc11_channels

    # 同一通道 CC7 至少 2 个（段落音量渐变）
    for channel in channels:
        values = [
            msg.value
            for track in midi.tracks
            for msg in track
            if msg.type == "control_change" and msg.control == 7 and msg.channel == channel
        ]
        assert len(values) >= 2
