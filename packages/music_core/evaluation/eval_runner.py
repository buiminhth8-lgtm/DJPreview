"""Evaluation Runner：批量生成 + 质量检查 + 特征打分。"""

from __future__ import annotations

import tempfile
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


def run_generation_eval(cases: list[EvalCase], render_audio: bool = False) -> EvalReport:
    """批量评估：只生成 MusicSpec + MIDI + QualityReport，不渲染 WAV（除非 render_audio）。"""
    results: list[EvalResult] = []
    for case in cases:
        try:
            spec = MockProvider().generate_music_spec(case.prompt)
            if case.style_template_id:
                template = get_style_template(case.style_template_id)
                spec = apply_style_template_to_music_spec(spec, template, 0.8)

            composition = compose_music(spec)
            with tempfile.TemporaryDirectory(prefix="aimusic_eval_") as tmp:
                midi_path = write_midi(composition, Path(tmp) / "output.mid")
                parsed = parse_midi_to_notes(midi_path)
            quality = check_arrangement_quality(spec, composition=composition, parsed_midi=parsed)

            trait_matches = _check_traits(spec, quality, case.expected_traits)
            trait_score = (sum(trait_matches.values()) / len(trait_matches)) * 100 if trait_matches else 0
            score = round(quality.score * 0.6 + trait_score * 0.4, 2)
            results.append(
                EvalResult(
                    case_id=case.id,
                    song_id=None,
                    score=score,
                    quality_score=round(quality.score, 2),
                    trait_matches=trait_matches,
                    warnings=[],
                    errors=[],
                )
            )
        except Exception as exc:  # noqa: BLE001 - 单用例失败不中断
            results.append(
                EvalResult(
                    case_id=case.id,
                    score=0.0,
                    quality_score=0.0,
                    trait_matches={},
                    warnings=[],
                    errors=[str(exc)],
                )
            )

    passed = sum(1 for r in results if r.score >= 60 and not r.errors)
    average = round(sum(r.score for r in results) / len(results), 2) if results else 0.0
    return EvalReport(
        created_at=datetime.now(timezone.utc).isoformat(),
        total_cases=len(results),
        passed_cases=passed,
        average_score=average,
        results=results,
        summary=f"共 {len(results)} 个用例，通过 {passed} 个，平均分 {average:.1f}",
    )
