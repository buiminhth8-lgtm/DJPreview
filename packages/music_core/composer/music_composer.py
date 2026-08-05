"""总作曲器：把 MusicSpec 编排成 CompositionResult。"""

from __future__ import annotations

import zlib

from packages.music_core.arrangement.arrangement_engine import ArrangementEngine
from packages.music_core.arrangement.pad_engine import PadEngine
from packages.music_core.arrangement.strings_engine import StringsEngine
from packages.music_core.bass.bass_engine import BassEngine
from packages.music_core.composer.events import CompositionResult, NoteEvent, TrackEvents, beats_per_bar
from packages.music_core.composer.expression import build_volume_curve, expression_cc11
from packages.music_core.drums.drum_engine import DrumEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.humanize.humanizer import Humanizer
from packages.music_core.melody.melody_engine import MelodyEngine
from packages.music_core.midi.midi_constants import DEFAULT_CHANNELS, DRUM_CHANNEL, GM_PROGRAMS
from services.api.schemas.music_spec import MusicSpec


def _humanize_seed(seed: int, track_id: str) -> int:
    """轨道级人性化种子：基于 seed + 轨道 id 的确定性哈希。"""
    return seed + zlib.crc32(track_id.encode("utf-8"))


def _split_strings_divisi(
    music_spec: MusicSpec,
    track: TrackSpec,
    notes: list[NoteEvent],
    channel_a: int,
    channel_b: int,
) -> list[TrackEvents]:
    """把弦乐声部按音高排序拆成两个分部（divisi），分置两个通道并加基础 pan。

    排序后交替分配（低音倾向低分部），两个分部各占 4 小节滑窗内的近似一半声部，
    保持确定性，不改变音符内容。
    """
    if not notes:
        return []
    ordered = sorted(notes, key=lambda n: (n.start_beat, n.pitch))
    group_a: list[NoteEvent] = []
    group_b: list[NoteEvent] = []
    for i, note in enumerate(ordered):
        (group_a if i % 2 == 0 else group_b).append(
            NoteEvent(
                pitch=note.pitch,
                start_beat=note.start_beat,
                duration_beats=note.duration_beats,
                velocity=note.velocity,
                channel=channel_a if i % 2 == 0 else channel_b,
                is_drum=False,
            )
        )
    curve = build_volume_curve(music_spec)
    tracks = [
        TrackEvents(
            track_id=f"{track.id}_divisi_a",
            name=f"{track.id}_strings_a",
            role=track.role or "strings",
            instrument=track.instrument or "string_ensemble_1",
            channel=channel_a,
            program=GM_PROGRAMS.get((track.instrument or "").strip().lower(), 0),
            notes=group_a,
            pan=52,
            cc_curve=curve,
            cc11=expression_cc11(),
        ),
        TrackEvents(
            track_id=f"{track.id}_divisi_b",
            name=f"{track.id}_strings_b",
            role=track.role or "strings",
            instrument=track.instrument or "string_ensemble_1",
            channel=channel_b,
            program=GM_PROGRAMS.get((track.instrument or "").strip().lower(), 0),
            notes=group_b,
            pan=76,
            cc_curve=curve,
            cc11=expression_cc11(),
        ),
    ]
    return tracks


def compose_music(music_spec: MusicSpec) -> CompositionResult:
    """编排 MusicSpec 生成 CompositionResult（确定性，依赖 music_spec.seed）。"""
    bar_harmony = build_bar_harmony(music_spec)
    bpb = beats_per_bar(music_spec)

    melody_engine = MelodyEngine()
    arrangement_engine = ArrangementEngine()
    pad_engine = PadEngine()
    strings_engine = StringsEngine()
    bass_engine = BassEngine()
    drum_engine = DrumEngine()

    tracks: list[TrackEvents] = []
    next_channel = 4

    for track in music_spec.tracks:
        role = (track.role or "").strip().lower()
        is_drum = role == "drums"
        if is_drum:
            channel = DRUM_CHANNEL
        elif role in DEFAULT_CHANNELS:
            channel = DEFAULT_CHANNELS[role]
        else:
            channel = next_channel
            next_channel += 1
            if channel == DRUM_CHANNEL:
                channel = next_channel
                next_channel += 1
            channel = min(channel, 15)

        program = None if is_drum else GM_PROGRAMS.get((track.instrument or "").strip().lower(), 0)
        track_events = TrackEvents(
            track_id=track.id,
            name=f"{track.id}_{role}" if role else track.id,
            role=role or "unknown",
            instrument=track.instrument or role,
            channel=channel,
            program=program,
        )

        if role == "melody":
            track_events.notes = melody_engine.generate(music_spec, bar_harmony, channel=channel)
        elif role == "drums":
            track_events.notes = drum_engine.generate(music_spec, bar_harmony, channel=channel)
        elif role == "bass":
            track_events.notes = bass_engine.generate(music_spec, bar_harmony, channel=channel)
        elif role == "pad":
            track_events.notes = pad_engine.generate(music_spec, bar_harmony, track, channel=channel)
        elif role == "strings":
            strings_notes = strings_engine.generate(music_spec, bar_harmony, track, channel=channel)
            # 弦乐 divisi：拆成两个分部通道，并附加 CC7/CC11 表达自动化
            second_channel = next_channel
            next_channel += 1
            if second_channel in (DRUM_CHANNEL, channel):
                second_channel = next_channel
                next_channel += 1
            second_channel = min(second_channel, 15)
            divisi = _split_strings_divisi(
                music_spec,
                track,
                strings_notes,
                channel_a=channel,
                channel_b=second_channel,
            )
            if divisi:
                tracks.extend(divisi)
                continue
            track_events.notes = strings_notes
            track_events.cc_curve = build_volume_curve(music_spec)
        else:
            # harmony / pad / strings / 未知角色：一律按伴奏处理
            track_events.notes = arrangement_engine.generate(music_spec, bar_harmony, track, channel=channel)
        tracks.append(track_events)

    # 轻度人性化（鼓组变化更小），保持确定性
    for track_events in tracks:
        if not track_events.notes:
            continue
        humanizer = Humanizer(_humanize_seed(music_spec.seed, track_events.track_id))
        track_events.notes = humanizer.humanize(track_events.notes, drum=(track_events.channel == DRUM_CHANNEL))

    # fallback：如果没有任何轨道有音符，生成基础钢琴伴奏保证结果非空
    if not any(t.notes for t in tracks):
        fallback = TrackEvents(
            track_id="fallback_piano",
            name="fallback_piano_harmony",
            role="harmony",
            instrument="acoustic_grand_piano",
            channel=1,
            program=0,
            notes=[
                NoteEvent(
                    pitch=pitch,
                    start_beat=round((bar.bar_index - 1) * bpb, 3),
                    duration_beats=4.0,
                    velocity=70,
                    channel=1,
                )
                for bar in bar_harmony
                for pitch in (bar.chord_pitches or [60, 64, 67])
            ],
        )
        tracks.append(fallback)

    return CompositionResult(
        title=music_spec.title,
        bpm=music_spec.tempo.bpm,
        ticks_per_beat=480,
        total_bars=music_spec.length.bars,
        beats_per_bar=bpb,
        tracks=tracks,
    )
