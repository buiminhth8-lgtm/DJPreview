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
    # ---------- Piano / Keyboard ----------
    "piano": "acoustic_grand_piano",
    "grand_piano": "acoustic_grand_piano",
    "grand_pianos": "acoustic_grand_piano",
    "keyboard": "acoustic_grand_piano",
    "keys": "acoustic_grand_piano",
    "cinematic_piano": "acoustic_grand_piano",
    "soft_piano": "acoustic_grand_piano",
    "solo_piano": "acoustic_grand_piano",
    "acoustic_piano": "acoustic_grand_piano",
    "epiano": "electric_piano_1",
    "electric_piano": "electric_piano_1",
    "electric_pianos": "electric_piano_1",
    "e_piano": "electric_piano_1",
    "rhodes": "electric_piano_1",
    "wurli": "electric_piano_1",

    # ---------- Guitar ----------
    "guitar": "acoustic_guitar_steel",
    "acoustic_guitar": "acoustic_guitar_steel",
    "acoustic_guitars": "acoustic_guitar_steel",
    "electric_guitar": "electric_guitar_clean",
    "electric_guitars": "electric_guitar_clean",
    "clean_guitar": "electric_guitar_clean",
    "clean_electric_guitar": "electric_guitar_clean",
    "dist_guitar": "distortion_guitar",
    "dist_guitars": "distortion_guitar",
    "rock_guitar": "distortion_guitar",
    "heavy_guitar": "distortion_guitar",
    "metal_guitar": "distortion_guitar",
    "power_chord_guitar": "distortion_guitar",
    "distortion_guitars": "distortion_guitar",
    "distorted_guitar": "distortion_guitar",
    "distorted_guitars": "distortion_guitar",
    "electric_guitar_distorted": "distortion_guitar",
    "distortion_guitar_electric": "distortion_guitar",
    "overdrive_guitar": "overdriven_guitar",
    "overdriven_guitars": "overdriven_guitar",
    "lead_guitar": "distortion_guitar",
    "rhythm_guitar": "electric_guitar_muted",
    "muted_guitar": "electric_guitar_muted",

    # ---------- Bass ----------
    "bass": "electric_bass_finger",
    "basses": "electric_bass_finger",
    "electric_bass": "electric_bass_finger",
    "electric_basses": "electric_bass_finger",
    "finger_bass": "electric_bass_finger",
    "fingerstyle_bass": "electric_bass_finger",
    "pick_bass": "electric_bass_pick",
    "picked_bass": "electric_bass_pick",
    "synth_bass": "synth_bass_1",
    "synth_basses": "synth_bass_1",
    "sub_bass": "synth_bass_1",
    "electronic_bass": "synth_bass_1",
    "electronic_basses": "synth_bass_1",
    "bass_synth": "synth_bass_1",
    "dub_bass": "synth_bass_1",

    # ---------- Strings ----------
    "strings": "string_ensemble_1",
    "string": "string_ensemble_1",
    "string_ensemble": "string_ensemble_1",
    "string_ensembles": "string_ensemble_1",
    "orchestral_strings": "string_ensemble_1",
    "cinematic_strings": "string_ensemble_1",
    "epic_strings": "string_ensemble_1",
    "string_ostinato": "string_ensemble_1",
    "string_section": "string_ensemble_1",
    "strings_section": "string_ensemble_1",
    "synth_strings": "synth_strings_1",
    "synth_strings_ensemble": "synth_strings_1",
    "violins": "violin",
    "violin_section": "string_ensemble_1",
    "cello_section": "cello",
    "cellos": "cello",

    # ---------- Brass ----------
    "brass": "brass_section",
    "brasses": "brass_section",
    "brass_section": "brass_section",
    "brass_sections": "brass_section",
    "brass_ensemble": "brass_section",
    "brass_ensembles": "brass_section",
    "epic_brass": "brass_section",
    "cinematic_brass": "brass_section",
    "orchestral_brass": "brass_section",
    "fanfare_brass": "brass_section",
    "horns": "brass_section",
    "horn_section": "brass_section",
    "trumpets": "trumpet",
    "trombones": "trombone",
    "french_horn": "french_horn",
    "french_horns": "french_horn",
    "horn": "french_horn",

    # ---------- Drums / Percussion ----------
    "drums": "standard_drum_kit",
    "drum": "standard_drum_kit",
    "drum_kit": "standard_drum_kit",
    "drumset": "standard_drum_kit",
    "drum_kits": "standard_drum_kit",
    "standard_drums": "standard_drum_kit",
    "percussion": "standard_drum_kit",
    "percussions": "standard_drum_kit",
    "drum_percussion": "standard_drum_kit",
    "heavy_drums": "standard_drum_kit",
    "heavy_rock_drums": "standard_drum_kit",
    "rock_drums": "standard_drum_kit",
    "metal_drums": "standard_drum_kit",
    "hard_drums": "standard_drum_kit",
    "power_drums": "standard_drum_kit",
    "epic_drums": "standard_drum_kit",
    "orchestral_percussion": "standard_drum_kit",
    "toms": "standard_drum_kit",
    "tom": "standard_drum_kit",
    "tom_drums": "standard_drum_kit",
    "low_tom": "standard_drum_kit",
    "mid_tom": "standard_drum_kit",
    "high_tom": "standard_drum_kit",
    "low_tom_percussion": "standard_drum_kit",
    "mid_tom_percussion": "standard_drum_kit",
    "high_tom_percussion": "standard_drum_kit",
    "tom_percussion": "standard_drum_kit",
    "kick": "standard_drum_kit",
    "kick_drum": "standard_drum_kit",
    "snare": "standard_drum_kit",
    "snare_drum": "standard_drum_kit",
    "cymbals": "standard_drum_kit",
    "crash_cymbal": "standard_drum_kit",
    "hi_hat": "standard_drum_kit",
    "hihat": "standard_drum_kit",
    "taiko": "standard_drum_kit",
    "taiko_drums": "standard_drum_kit",
    "taiko_percussion": "standard_drum_kit",
    "cinematic_drums": "standard_drum_kit",
    "cinematic_percussion": "standard_drum_kit",
    "battle_drums": "standard_drum_kit",
    "military_drums": "standard_drum_kit",

    # ---------- Pad / Synth ----------
    "pad": "pad_2_warm",
    "pads": "pad_2_warm",
    "synth_pad": "pad_2_warm",
    "synth_pads": "pad_2_warm",
    "warm_pad": "pad_2_warm",
    "warm_pads": "pad_2_warm",
    "pad_warm": "pad_2_warm",
    "ambient_pad": "pad_1_new_age",
    "ambient_pads": "pad_1_new_age",
    "atmospheric_pad": "pad_1_new_age",
    "dream_pad": "pad_2_warm",
    "soft_pad": "pad_2_warm",
    "lead": "lead_2_sawtooth",
    "leads": "lead_2_sawtooth",
    "synth_lead": "lead_2_sawtooth",
    "synth_leads": "lead_2_sawtooth",
    "lead_synth": "lead_1_square",
    "lead_synths": "lead_1_square",
    "lead_square": "lead_1_square",
    "square_lead": "lead_1_square",
    "sawtooth_lead": "lead_2_sawtooth",
    "saw_lead": "lead_2_sawtooth",
    "sawtooth": "lead_2_sawtooth",

    # ---------- Woodwind / Ethnic ----------
    "flute": "flute",
    "flutes": "flute",
    "pan_flute": "pan_flute",
    "shakuhachi": "shakuhachi",
    "erhu": "erhu",
    "koto": "koto",
    "shamisen": "shamisen",
    "dizi": "flute",
    "bamboo_flute": "pan_flute",
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


# 角色感知关键词：当 role 明确时优先按角色归一化
_DRUM_KEYWORDS = ("drum", "percussion", "tom", "kick", "snare", "cymbal", "hi_hat", "hihat", "taiko")
_BASS_KEYWORDS = ("bass",)


def _resolve_canonical(key: str, role: str | None = None) -> str:
    """别名/复数解析为 canonical id；未知返回 key。"""
    if key in INSTRUMENTS:
        return key
    target = INSTRUMENT_ALIASES.get(key)
    if target is not None:
        return target
    # 常见复数：去掉尾部 s 再查一次（strings→string, drums→drum, horns→horn, violins→violin）
    if key.endswith("s") and len(key) > 3:
        singular = key[:-1]
        target = INSTRUMENT_ALIASES.get(singular)
        if target is not None:
            return target
        if singular in INSTRUMENTS:
            return singular
    return key


def normalize_instrument_name(name: str | None, role: str | None = None) -> str:
    """返回 canonical instrument id；未知乐器返回规范化后的原字符串。

    role 可选，用于角色感知归一化：
      - role=drums 时，drum / percussion / tom / kick / snare / cymbal 类 → standard_drum_kit
      - role=bass 时，bass 类优先映射到 bass canonical
    """
    key = _normalize_name(name)
    if not key:
        return ""

    canonical = _resolve_canonical(key, role)
    if canonical in INSTRUMENTS:
        return canonical

    # 角色感知兜底（别名表未覆盖时）
    if role == "drums" and any(kw in key for kw in _DRUM_KEYWORDS):
        return "standard_drum_kit"
    if role == "bass" and any(kw in key for kw in _BASS_KEYWORDS):
        return "electric_bass_finger"
    return canonical


def canonical_instrument_name(name: str | None, role: str | None = None) -> str:
    """normalize_instrument_name 的别名（更语义化命名）。"""
    return normalize_instrument_name(name, role=role)


def is_known_instrument(name: str | None) -> bool:
    """判断乐器名是否可解析为 canonical id。"""
    return normalize_instrument_name(name) in INSTRUMENTS


def resolve_instrument(name: str | None, role: str | None = None) -> InstrumentInfo:
    """解析乐器信息；未知乐器返回 unknown 占位（不崩溃，gm_program=None）。"""
    canonical = normalize_instrument_name(name, role=role)
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


def get_gm_program(name: str | None, default: int = 0, role: str | None = None) -> int:
    """乐器 → 0-based GM program；未知或鼓组返回 default。"""
    program = resolve_instrument(name, role=role).gm_program
    return default if program is None else program


def is_drum_instrument(name: str | None, role: str | None = None) -> bool:
    """判断乐器是否属于 GM 鼓组（走 drum channel 9）。"""
    return resolve_instrument(name, role=role).is_drum


def list_instruments() -> list[InstrumentInfo]:
    """返回全部 canonical 乐器信息（按 id 排序）。"""
    return sorted(INSTRUMENTS.values(), key=lambda item: item.id)
