"""MIDI 常量：GM 音色、鼓组音色与通道分配。"""

from packages.music_core.instruments.gm import GM_PROGRAMS as _CANONICAL_GM_PROGRAMS
from packages.music_core.instruments.registry import INSTRUMENT_ALIASES

DRUM_CHANNEL = 9  # GM 第 10 通道（MIDI 内部编号 9）

# 统一乐器 → GM program（canonical + alias，来自 Instrument Registry）
GM_PROGRAMS: dict[str, int] = dict(_CANONICAL_GM_PROGRAMS)
for _alias, _canonical in INSTRUMENT_ALIASES.items():
    if _canonical in _CANONICAL_GM_PROGRAMS:
        GM_PROGRAMS.setdefault(_alias, _CANONICAL_GM_PROGRAMS[_canonical])

# 常用鼓音色（GM 标准）
DRUM_NOTES: dict[str, int] = {
    "kick": 36,
    "snare": 38,
    "side_stick": 37,
    "clap": 39,
    "low_tom": 45,
    "mid_tom": 47,
    "high_tom": 50,
    "pedal_hihat": 44,
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
