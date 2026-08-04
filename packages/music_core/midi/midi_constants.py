"""MIDI 常量：GM 音色、鼓组音色与通道分配。"""

DRUM_CHANNEL = 9  # GM 第 10 通道（MIDI 内部编号 9）

# 乐器 → GM program（未知乐器默认 acoustic_grand_piano=0）
GM_PROGRAMS: dict[str, int] = {
    "acoustic_grand_piano": 0,
    "piano": 0,
    "bright_acoustic_piano": 1,
    "electric_piano_1": 4,
    "electric_piano": 4,
    "acoustic_guitar_nylon": 24,
    "acoustic_guitar_steel": 25,
    "electric_guitar_clean": 27,
    "acoustic_bass": 32,
    "electric_bass_finger": 33,
    "bass": 33,
    "violin": 40,
    "string_ensemble": 48,
    "strings": 48,
    "synth_strings": 50,
    "choir_aahs": 52,
    "pad_warm": 89,
    "pad": 89,
    "synth_pad": 90,
    "lead_synth": 80,
    "synth_lead": 80,
    "lead_square": 80,
    "synth_bass": 38,
}

# 常用鼓音色（GM 标准）
DRUM_NOTES: dict[str, int] = {
    "kick": 36,
    "snare": 38,
    "closed_hihat": 42,
    "open_hihat": 46,
    "crash": 49,
    "ride": 51,
}

# 默认通道分配（鼓组固定 9）
DEFAULT_CHANNELS: dict[str, int] = {
    "melody": 0,
    "harmony": 1,
    "bass": 2,
    "pad": 3,
    "strings": 3,
}
