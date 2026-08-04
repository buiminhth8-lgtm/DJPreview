"""GM（General MIDI）program 映射（统一 0-based，可直接写入 MIDI program_change）。"""

from __future__ import annotations

# canonical instrument id → 0-based GM program
GM_PROGRAMS: dict[str, int] = {
    # 钢琴
    "acoustic_grand_piano": 0,
    "bright_acoustic_piano": 1,
    "electric_grand_piano": 2,
    "honky_tonk_piano": 3,
    "electric_piano_1": 4,
    "electric_piano_2": 5,
    # 吉他
    "acoustic_guitar_nylon": 24,
    "acoustic_guitar_steel": 25,
    "electric_guitar_jazz": 26,
    "electric_guitar_clean": 27,
    "electric_guitar_muted": 28,
    "overdriven_guitar": 29,
    "distortion_guitar": 30,
    # 贝斯
    "acoustic_bass": 32,
    "electric_bass_finger": 33,
    "electric_bass_pick": 34,
    "fretless_bass": 35,
    "slap_bass_1": 36,
    "slap_bass_2": 37,
    "synth_bass_1": 38,
    "synth_bass_2": 39,
    # 弦乐
    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "string_ensemble_1": 48,
    "string_ensemble_2": 49,
    "synth_strings_1": 50,
    "synth_strings_2": 51,
    # 人声
    "choir_aahs": 52,
    "voice_oohs": 53,
    "synth_voice": 54,
    # 铜管
    "trumpet": 56,
    "trombone": 57,
    "french_horn": 60,
    "brass_section": 61,
    # 萨克斯
    "soprano_sax": 64,
    "alto_sax": 65,
    "tenor_sax": 66,
    "baritone_sax": 67,
    # 木管
    "flute": 73,
    "pan_flute": 75,
    "shakuhachi": 77,
    # 合成主音 / pad
    "lead_1_square": 80,
    "lead_2_sawtooth": 81,
    "pad_1_new_age": 88,
    "pad_2_warm": 89,
    "pad_3_polysynth": 90,
    "pad_4_choir": 91,
    "pad_5_bowed": 92,
    "pad_6_metallic": 93,
    "pad_7_halo": 94,
    "pad_8_sweep": 95,
    # 民族乐器
    "shamisen": 106,
    "koto": 107,
    "erhu": 110,
    "shanai": 111,
}
