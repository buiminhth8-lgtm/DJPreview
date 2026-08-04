"""分轨 WAV stems 渲染与打包。"""

from __future__ import annotations

import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.midi.midi_splitter import split_composition_to_track_midis
from packages.music_core.mix.mix_engine import apply_mix_to_composition
from packages.music_core.mix.mix_models import MixSpec
from packages.renderer.factory import get_audio_renderer
from services.api.schemas.music_spec import MusicSpec

logger = logging.getLogger(__name__)


@dataclass
class StemExportResult:
    generated_at: str
    renderer: str
    tracks: list[dict]
    zip_file: str
    warnings: list[str] = field(default_factory=list)
    stems_dir: Path | None = None


def export_stems(
    song_id: str,
    music_spec: MusicSpec,
    mix_spec: MixSpec,
    output_dir: str | Path,
    *,
    sample_rate: int = 44100,
    gain: float = 0.6,
) -> StemExportResult:
    """生成分轨 MIDI + WAV + stems.zip + stems_metadata.json。"""
    output_dir = Path(output_dir)
    midi_dir = output_dir / "midi"
    wav_dir = output_dir / "wav"

    composition = compose_music(music_spec)
    composition = apply_mix_to_composition(composition, mix_spec)
    warnings = list(composition.warnings)

    split_results = split_composition_to_track_midis(composition, midi_dir)
    renderer = get_audio_renderer()
    tracks_meta: list[dict] = []

    for item in split_results:
        midi_path = Path(item["path"])
        wav_path = wav_dir / f"{item['track_id']}.wav"
        try:
            result = renderer.render_wav(midi_path, wav_path, sample_rate=sample_rate, gain=gain)
            tracks_meta.append(
                {
                    "track_id": item["track_id"],
                    "role": item["role"],
                    "midi_file": f"midi/{item['file']}",
                    "wav_file": f"wav/{item['track_id']}.wav",
                    "file_size": result.file_size,
                    "note_count": item["note_count"],
                }
            )
        except Exception as exc:  # noqa: BLE001 - 单轨失败记录 warning，不中断整体导出
            warnings.append(f"轨道 {item['track_id']} WAV 渲染失败：{exc}")
            logger.warning("stem render failed for %s: %s", item["track_id"], exc)

    zip_path = output_dir / "stems.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(midi_dir.glob("*.mid")):
            zf.write(path, f"midi/{path.name}")
        for path in sorted(wav_dir.glob("*.wav")):
            zf.write(path, f"wav/{path.name}")

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "renderer": renderer.name,
        "tracks": tracks_meta,
        "zip_file": "stems.zip",
        "warnings": warnings,
    }
    (output_dir / "stems_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return StemExportResult(
        generated_at=metadata["generated_at"],
        renderer=renderer.name,
        tracks=tracks_meta,
        zip_file="stems.zip",
        warnings=warnings,
        stems_dir=output_dir,
    )
