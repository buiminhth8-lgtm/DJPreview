"""乐器注册表：canonical id、别名、GM program、family、默认角色与鼓组标记。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from packages.music_core.instruments.gm import GM_PROGRAMS


@dataclass(frozen=True)
class InstrumentInfo:
    id: str
    gm_program: int | None
    family: str
    default_role: str | None = None
    is_drum: bool = False
    aliases: tuple[str, ...] = ()


# 别名 → canonical id
INSTRUMENT_ALIASES: dict[str, str] = {
    "piano": "acoustic_grand_piano",
    "grand_piano": "acoustic_grand_piano",
    "keyboard": "acoustic_grand_piano",
    "epiano": "electric_piano_1",
    "electric_piano": "electric_piano_1",
    "guitar": "acoustic_guitar_steel",
    "acoustic_guitar": "acoustic_guitar_steel",
    "electric_guitar": "electric_guitar_clean",
    "dist_guitar": "distortion_guitar",
    "rock_guitar": "distortion_guitar",
    "bass": "electric_bass_finger",
    "electric_bass": "electric_bass_finger",
    "synth_bass": "synth_bass_1",
    "strings": "string_ensemble_1",
    "string_ensemble": "string_ensemble_1",
    "orchestral_strings": "string_ensemble_1",
    "synth_strings": "synth_strings_1",
    "pad": "pad_2_warm",
    "synth_pad": "pad_2_warm",
    "warm_pad": "pad_2_warm",
    "pad_warm": "pad_2_warm",
    "ambient_pad": "pad_1_new_age",
    "lead": "lead_2_sawtooth",
    "synth_lead": "lead_2_sawtooth",
    "lead_synth": "lead_1_square",
    "lead_square": "lead_1_square",
    "flute": "flute",
    "pan_flute": "pan_flute",
    "erhu": "erhu",
    "koto": "koto",
    "shamisen": "shamisen",
    "drums": "standard_drum_kit",
    "drum": "standard_drum_kit",
    "drum_kit": "standard_drum_kit",
    "standard_drums": "standard_drum_kit",
}


# canonical id → (program, family, default_role, is_drum)
_CANONICAL_SPECS: dict[str, tuple[int | None, str, str | None, bool]] = {
    "acoustic_grand_piano": (0, "piano", "harmony", False),
    "bright_acoustic_piano": (1, "piano", "harmony", False),
    "electric_grand_piano": (2, "piano", "harmony", False),
    "honky_tonk_piano": (3, "piano", "harmony", False),
    "electric_piano_1": (4, "piano", "harmony", False),
    "electric_piano_2": (5, "piano", "harmony", False),
    "acoustic_guitar_nylon": (24, "guitar", "harmony", False),
    "acoustic_guitar_steel": (25, "guitar", "harmony", False),
    "electric_guitar_jazz": (26, "guitar", "harmony", False),
    "electric_guitar_clean": (27, "guitar", "harmony", False),
    "electric_guitar_muted": (28, "guitar", "harmony", False),
    "overdriven_guitar": (29, "guitar", "harmony", False),
    "distortion_guitar": (30, "guitar", "harmony", False),
    "acoustic_bass": (32, "bass", "bass", False),
    "electric_bass_finger": (33, "bass", "bass", False),
    "electric_bass_pick": (34, "bass", "bass", False),
    "fretless_bass": (35, "bass", "bass", False),
    "slap_bass_1": (36, "bass", "bass", False),
    "slap_bass_2": (37, "bass", "bass", False),
    "synth_bass_1": (38, "bass", "bass", False),
    "synth_bass_2": (39, "bass", "bass", False),
    "violin": (40, "strings", "melody", False),
    "viola": (41, "strings", "melody", False),
    "cello": (42, "strings", "pad", False),
    "contrabass": (43, "strings", "bass", False),
    "string_ensemble_1": (48, "strings", "pad", False),
    "string_ensemble_2": (49, "strings", "pad", False),
    "synth_strings_1": (50, "strings", "pad", False),
    "synth_strings_2": (51, "strings", "pad", False),
    "choir_aahs": (52, "voice", "pad", False),
    "voice_oohs": (53, "voice", "pad", False),
    "synth_voice": (54, "voice", "melody", False),
    "trumpet": (56, "brass", "melody", False),
    "trombone": (57, "brass", "harmony", False),
    "french_horn": (60, "brass", "harmony", False),
    "brass_section": (61, "brass", "harmony", False),
    "soprano_sax": (64, "sax", "melody", False),
    "alto_sax": (65, "sax", "melody", False),
    "tenor_sax": (66, "sax", "melody", False),
    "baritone_sax": (67, "sax", "harmony", False),
    "flute": (73, "woodwind", "melody", False),
    "pan_flute": (75, "woodwind", "melody", False),
    "shakuhachi": (77, "woodwind", "melody", False),
    "lead_1_square": (80, "synth_lead", "melody", False),
    "lead_2_sawtooth": (81, "synth_lead", "melody", False),
    "pad_1_new_age": (88, "synth_pad", "pad", False),
    "pad_2_warm": (89, "synth_pad", "pad", False),
    "pad_3_polysynth": (90, "synth_pad", "pad", False),
    "pad_4_choir": (91, "synth_pad", "pad", False),
    "pad_5_bowed": (92, "synth_pad", "pad", False),
    "pad_6_metallic": (93, "synth_pad", "pad", False),
    "pad_7_halo": (94, "synth_pad", "pad", False),
    "pad_8_sweep": (95, "synth_pad", "pad", False),
    "shamisen": (106, "ethnic", "melody", False),
    "koto": (107, "ethnic", "melody", False),
    "erhu": (110, "ethnic", "melody", False),
    "shanai": (111, "ethnic", "melody", False),
    "standard_drum_kit": (None, "drums", "drums", True),
}


def _build_instruments() -> dict[str, InstrumentInfo]:
    result: dict[str, InstrumentInfo] = {}
    for canonical, (program, family, default_role, is_drum) in _CANONICAL_SPECS.items():
        aliases = tuple(
            alias for alias, target in INSTRUMENT_ALIASES.items() if target == canonical
        )
        result[canonical] = InstrumentInfo(
            id=canonical,
            gm_program=program,
            family=family,
            default_role=default_role,
            is_drum=is_drum,
            aliases=aliases,
        )
    return result


INSTRUMENTS: dict[str, InstrumentInfo] = _build_instruments()


def _normalize_name(name: str | None) -> str:
    """规范化：小写、空格/短横线 → 下划线、合并连续下划线。"""
    text = (name or "").strip().lower()
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def normalize_instrument_name(name: str | None) -> str:
    """返回 canonical instrument id；未知乐器返回规范化后的原字符串。"""
    key = _normalize_name(name)
    if not key:
        return ""
    if key in INSTRUMENTS:
        return key
    return INSTRUMENT_ALIASES.get(key, key)


def is_known_instrument(name: str | None) -> bool:
    """判断乐器名是否可解析为 canonical id。"""
    return normalize_instrument_name(name) in INSTRUMENTS


def resolve_instrument(name: str | None) -> InstrumentInfo:
    """解析乐器信息；未知乐器返回 unknown 占位（不崩溃，gm_program=None）。"""
    canonical = normalize_instrument_name(name)
    info = INSTRUMENTS.get(canonical)
    if info is not None:
        return info
    return InstrumentInfo(
        id=canonical or "unknown",
        gm_program=None,
        family="unknown",
        default_role=None,
        is_drum=False,
    )


def get_gm_program(name: str | None, default: int = 0) -> int:
    """乐器 → 0-based GM program；未知或鼓组返回 default。"""
    program = resolve_instrument(name).gm_program
    return default if program is None else program


def is_drum_instrument(name: str | None) -> bool:
    """判断乐器是否属于 GM 鼓组（走 drum channel 9）。"""
    return resolve_instrument(name).is_drum


def list_instruments() -> list[InstrumentInfo]:
    """返回全部 canonical 乐器信息（按 id 排序）。"""
    return sorted(INSTRUMENTS.values(), key=lambda item: item.id)
