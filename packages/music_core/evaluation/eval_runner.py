"""Evaluation Runner：批量生成 + MIDI + Quality + 可选音频渲染。"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from packages.llm.mock_provider import MockProvider
from packages.music_core.analysis.midi_parser import parse_midi_to_notes
from packages.music_core.analysis.quality_checker import check_arrangement_quality
from packages.music_core.composer.music_composer import compose_music
from packages.music_core.evaluation.eval_models import EvalCase, EvalReport, EvalResult
from packages.music_core.midi.midi_writer import write_midi
from packages.music_core.styles.style_applier import apply_style_template_to_music_spec
from packages.music_core.styles.style_library import get_style_template
from packages.renderer.audio_metadata import get_wav_duration_seconds
from packages.renderer.factory import get_audio_renderer

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^0-9A-Za-z_-]+")


def _safe_case_dirname(case_id: str, index: int) -> str:
    """生成安全的 case 目录名（case_001_case_id）。"""
    safe = _SAFE_NAME.sub("_", case_id) or "case"
    return f"case_{index:03d}_{safe}"


def _check_traits(spec, quality, traits: dict) -> dict:
    matches: dict[str, bool] = {}
    for key, value in traits.items():
        if key == "tempo_range":
            low, high = value
            matches[key] = low <= spec.tempo.bpm <= high
        elif key == "mode":
            matches[key] = spec.tonality.mode == value
        elif key == "scale":
            matches[key] = bool(spec.tonality.scale and value in spec.tonality.scale)
        elif key == "has_track_role":
            matches[key] = any(t.role == value for t in spec.tracks)
        elif key == "has_track_role2":
            matches[key] = any(t.role == value for t in spec.tracks)
        elif key == "style_contains":
            matches[key] = value in " ".join(spec.style)
        elif key == "min_quality_score":
            matches[key] = quality.score >= value
        else:
            matches[key] = False
    return matches


def _render_case_audio(case_dir: Path, midi_path: Path, result: EvalResult) -> None:
    """渲染单个 case 的 WAV；失败记录到 result，不抛出。"""
    try:
        renderer = get_audio_renderer()
        wav_path = case_dir / "output.wav"
        render_result = renderer.render_wav(
            midi_path,
            wav_path,
            sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "44100")),
            gain=float(os.getenv("AUDIO_GAIN", "0.6")),
        )
        result.audio_rendered = True
        result.audio_path = str(wav_path)
        result.audio_duration_seconds = render_result.duration_seconds or get_wav_duration_seconds(wav_path)
        result.renderer = render_result.renderer or getattr(renderer, "name", None)
        if render_result.warnings:
            result.warnings.extend(render_result.warnings)
        metadata = {
            "renderer": result.renderer,
            "sample_rate": render_result.sample_rate,
            "duration_seconds": result.audio_duration_seconds,
            "file_size": render_result.file_size,
            "warnings": render_result.warnings,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
        }
        (case_dir / "audio_metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 - 单个 case 渲染失败不影响整体评估
        result.audio_rendered = False
        result.render_error = str(exc)
        result.warnings.append("Audio rendering failed for this case.")
        logger.warning("评估用例音频渲染失败：%s", exc)


def run_generation_eval(
    cases: list[EvalCase],
    render_audio: bool = False,
    output_dir: Path | str | None = None,
) -> EvalReport:
    """批量评估：每个 case 生成 MusicSpec + MIDI + QualityReport。

    render_audio=False：不调用任何音频渲染器，不生成 WAV。
    render_audio=True：使用 renderer factory 渲染 WAV 并保存 audio_metadata.json；
    单个 case 渲染失败不会中断整体评估，失败信息记录在该 case 的 result 中。
    """
    run_id = uuid.uuid4().hex[:12]
    base_dir = Path(output_dir) if output_dir is not None else Path(
        os.getenv("EVALUATIONS_DIR", "data/evaluations")
    )
    run_dir = base_dir / run_id
    cases_dir = run_dir / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    report_warnings: list[str] = []
    results: list[EvalResult] = []
    for index, case in enumerate(cases, start=1):
        case_dir = cases_dir / _safe_case_dirname(case.id, index)
        case_dir.mkdir(parents=True, exist_ok=True)
        try:
            spec = MockProvider().generate_music_spec(case.prompt)
            if case.style_template_id:
                template = get_style_template(case.style_template_id)
                spec = apply_style_template_to_music_spec(spec, template, 0.8)

            composition = compose_music(spec)
            midi_path = write_midi(composition, case_dir / "output.mid")
            parsed = parse_midi_to_notes(midi_path)
            quality = check_arrangement_quality(spec, composition=composition, parsed_midi=parsed)
            (case_dir / "music_spec.json").write_text(
                spec.model_dump_json(indent=2),
                encoding="utf-8",
            )
            (case_dir / "quality_report.json").write_text(
                json.dumps(quality.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            trait_matches = _check_traits(spec, quality, case.expected_traits)
            trait_score = (sum(trait_matches.values()) / len(trait_matches)) * 100 if trait_matches else 0
            score = round(quality.score * 0.6 + trait_score * 0.4, 2)
            result = EvalResult(
                case_id=case.id,
                song_id=None,
                score=score,
                quality_score=round(quality.score, 2),
                trait_matches=trait_matches,
                music_spec=spec.model_dump(mode="json"),
                midi_path=str(midi_path),
                quality_report=quality.model_dump(mode="json"),
                render_audio=render_audio,
                warnings=[],
                errors=[],
            )
            if render_audio:
                _render_case_audio(case_dir, midi_path, result)
            results.append(result)
        except Exception as exc:  # noqa: BLE001 - 单用例失败不中断
            logger.warning("评估用例 %s 失败：%s", case.id, exc)
            results.append(
                EvalResult(
                    case_id=case.id,
                    score=0.0,
                    quality_score=0.0,
                    trait_matches={},
                    render_audio=render_audio,
                    warnings=[],
                    errors=[str(exc)],
                )
            )
            report_warnings.append(f"评估用例 {case.id} 失败：{exc}")

    passed = sum(1 for r in results if r.score >= 60 and not r.errors)
    failed = len(results) - passed
    average = round(sum(r.score for r in results) / len(results), 2) if results else 0.0
    audio_rendered_cases = sum(1 for r in results if r.audio_rendered)
    audio_failed_cases = sum(1 for r in results if r.render_audio and not r.audio_rendered)
    return EvalReport(
        render_audio=render_audio,
        total_cases=len(results),
        passed_cases=passed,
        failed_cases=failed,
        average_score=average,
        audio_rendered_cases=audio_rendered_cases,
        audio_failed_cases=audio_failed_cases,
        results=results,
        warnings=report_warnings,
        summary=f"共 {len(results)} 个用例，通过 {passed} 个，平均分 {average:.1f}，"
        f"音频渲染成功 {audio_rendered_cases} 个，失败 {audio_failed_cases} 个",
    )
