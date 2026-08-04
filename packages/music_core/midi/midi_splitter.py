"""MIDI 分轨导出：CompositionResult → 每轨一个 .mid 文件。"""

from __future__ import annotations

from pathlib import Path

from packages.music_core.composer.events import CompositionResult
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.mix.mix_engine import apply_mix_to_composition
from packages.music_core.mix.mix_models import MixSpec


def split_composition_to_track_midis(
    composition: CompositionResult,
    output_dir: str | Path,
    mix_spec: MixSpec | None = None,
) -> list[dict]:
    """按轨道拆分导出单轨 MIDI；返回 [{track_id, role, file, path, note_count}]。"""
    if mix_spec is not None:
        composition = apply_mix_to_composition(composition, mix_spec)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    for track_events in composition.tracks:
        if not track_events.notes:
            continue
        single = CompositionResult(
            song_id=composition.song_id,
            title=composition.title,
            bpm=composition.bpm,
            ticks_per_beat=composition.ticks_per_beat,
            total_bars=composition.total_bars,
            beats_per_bar=composition.beats_per_bar,
            tracks=[track_events],
        )
        filename = f"{track_events.track_id}.mid"
        path = output_dir / filename
        write_midi(single, path)
        results.append(
            {
                "track_id": track_events.track_id,
                "role": track_events.role,
                "file": filename,
                "path": str(path),
                "note_count": len(track_events.notes),
            }
        )
    return results
