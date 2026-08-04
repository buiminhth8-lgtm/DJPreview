"""第二阶段 MIDI 质量审查测试：旋律调内、贝斯根音、鼓组通道、MIDI 元事件。"""

import mido

from packages.llm.mock_provider import MockProvider
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.composer.events import beats_per_bar
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.midi.midi_constants import DRUM_CHANNEL
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.theory.scales import get_scale_pitches


def _spec(seed: int = 1234):
    spec = MockProvider().generate_music_spec("生成一段忧郁空灵的钢琴配乐")
    spec.seed = seed
    return spec


def test_melody_pitches_stay_in_key():
    spec = _spec()
    result = compose_music(spec)
    scale_mods = {p % 12 for p in get_scale_pitches(spec.tonality.key, spec.tonality.mode, 4)}
    melody = next(t for t in result.tracks if t.role == "melody")
    assert melody.notes
    assert all((n.pitch % 12) in scale_mods for n in melody.notes)
    assert len({n.pitch for n in melody.notes}) >= 8


def test_bass_follows_chord_root_and_fifth():
    spec = _spec()
    harmony = build_bar_harmony(spec)
    result = compose_music(spec)
    bass = next(t for t in result.tracks if t.role == "bass")
    bpb = beats_per_bar(spec)

    for bar in harmony:
        root_mod = (bar.chord_pitches[0] if bar.chord_pitches else 60) % 12
        allowed_mods = {root_mod, (root_mod + 7) % 12}
        bar_notes = [
            n
            for n in bass.notes
            # 人性化会把小节首拍轻微前移（±0.012），用 +0.02 容差做 floor 归属
            if int((n.start_beat + 0.02) // bpb) + 1 == bar.bar_index
        ]
        assert bar_notes, f"bar {bar.bar_index} 缺少贝斯音符"
        for note in bar_notes:
            assert 36 <= note.pitch <= 52, f"bar {bar.bar_index} 音域越界: {note.pitch}"
            assert note.pitch % 12 in allowed_mods, (
                f"bar {bar.bar_index} {bar.chord_symbol} 根音级={root_mod}，"
                f"贝斯音 {note.pitch} (mod {note.pitch % 12}) 不是根音或纯五度"
            )


def test_drums_use_gm_channel_9():
    spec = _spec()
    result = compose_music(spec)
    drums = next(t for t in result.tracks if t.role == "drums")
    assert drums.notes
    assert all(n.channel == DRUM_CHANNEL and n.is_drum for n in drums.notes)
    assert all(n.pitch in {36, 38, 42, 46, 49, 51} for n in drums.notes)


def test_midi_writer_meta_and_events(tmp_path):
    spec = _spec()
    result = compose_music(spec)
    output = write_midi(result, tmp_path / "quality.mid")
    midi = mido.MidiFile(str(output))

    tempo = [m for t in midi.tracks for m in t if m.type == "set_tempo"]
    time_sigs = [m for t in midi.tracks for m in t if m.type == "time_signature"]
    programs = [m for t in midi.tracks for m in t if m.type == "program_change"]
    ons = [m for t in midi.tracks for m in t if m.type == "note_on"]
    offs = [m for t in midi.tracks for m in t if m.type == "note_off"]

    assert len(tempo) == 1
    assert len(time_sigs) == 1
    assert (time_sigs[0].numerator, time_sigs[0].denominator) == (4, 4)
    assert len(programs) >= 4  # melody/harmony/bass/pad，不含鼓
    assert len(ons) == len(offs) > 0
    # 鼓组音符必须全部在 channel 9
    drum_ons = [m for m in ons if m.channel == DRUM_CHANNEL]
    assert drum_ons and all(m.velocity > 0 for m in drum_ons)
    # 所有音符力度合法
    assert all(1 <= m.velocity <= 127 for m in ons)


def test_compose_flow_and_determinism():
    spec = _spec(seed=999)
    r1 = compose_music(spec)
    r2 = compose_music(spec)
    flat = lambda r: {
        t.role: [(n.pitch, n.start_beat, n.duration_beats, n.velocity) for n in t.notes]
        for t in r.tracks
    }
    assert flat(r1) == flat(r2)
    assert {t.role for t in r1.tracks} == {"melody", "harmony", "bass", "drums", "pad"}
    assert all(t.notes for t in r1.tracks)
