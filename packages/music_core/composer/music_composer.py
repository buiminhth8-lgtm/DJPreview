"""总作曲器：把 MusicSpec 编排成 CompositionResult。"""

from __future__ import annotations

import zlib

from packages.music_core.arrangement.arrangement_engine import ArrangementEngine
from packages.music_core.arrangement.pad_engine import PadEngine
from packages.music_core.arrangement.strings_engine import StringsEngine
from packages.music_core.bass.bass_engine import BassEngine
from packages.music_core.composer.events import CompositionResult, NoteEvent, TrackEvents, beats_per_bar
from packages.music_core.drums.drum_engine import DrumEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.humanize.humanizer import Humanizer
from packages.music_core.melody.melody_engine import MelodyEngine
from packages.music_core.midi.midi_constants import DEFAULT_CHANNELS, DRUM_CHANNEL, GM_PROGRAMS
from services.api.schemas.music_spec import MusicSpec


def _humanize_seed(seed: int, track_id: str) -> int:
    """轨道级人性化种子：基于 seed + 轨道 id 的确定性哈希。"""
    return seed + zlib.crc32(track_id.encode("utf-8"))


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
            track_events.notes = strings_engine.generate(music_spec, bar_harmony, track, channel=channel)
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
