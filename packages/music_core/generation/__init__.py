"""旋律/和声/能量生成增强模块。"""

from packages.music_core.generation.arrangement_curve import build_arrangement_curve
from packages.music_core.generation.cadence_engine import enhance_harmony_with_cadences, suggest_section_cadence
from packages.music_core.generation.motif_engine import (
    GenerationContext,
    Motif,
    MotifNote,
    create_motif,
    motif_to_note_events,
    transform_motif,
)

__all__ = [
    "GenerationContext",
    "Motif",
    "MotifNote",
    "build_arrangement_curve",
    "create_motif",
    "enhance_harmony_with_cadences",
    "motif_to_note_events",
    "suggest_section_cadence",
    "transform_motif",
]
