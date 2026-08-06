"""统一乐器注册表（T17）：canonical id / alias / GM program / 鼓组标记。"""

from packages.music_core.instruments.gm import GM_PROGRAMS
from packages.music_core.instruments.registry import (
    INSTRUMENT_ALIASES,
    INSTRUMENTS,
    InstrumentInfo,
    canonical_instrument_name,
    get_gm_program,
    is_drum_instrument,
    is_known_instrument,
    list_instruments,
    normalize_instrument_name,
    resolve_instrument,
)

__all__ = [
    "GM_PROGRAMS",
    "INSTRUMENT_ALIASES",
    "INSTRUMENTS",
    "InstrumentInfo",
    "canonical_instrument_name",
    "get_gm_program",
    "is_drum_instrument",
    "is_known_instrument",
    "list_instruments",
    "normalize_instrument_name",
    "resolve_instrument",
]
