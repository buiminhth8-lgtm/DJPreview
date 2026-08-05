"""鼓组 groove 模式库（T20）：风格化 kick/snare/hat/cymbal/tom + fill。"""

from __future__ import annotations

import random

from packages.music_core.composer.drum_models import DrumHit

# GM 标准鼓组 note（MIDI channel 9）
GM_DRUM_NOTES = {
    "kick": 36,
    "side_stick": 37,
    "snare": 38,
    "clap": 39,
    "low_tom": 45,
    "mid_tom": 47,
    "high_tom": 50,
    "closed_hat": 42,
    "pedal_hat": 44,
    "open_hat": 46,
    "crash": 49,
    "ride": 51,
}

_KICK = GM_DRUM_NOTES["kick"]
_SNARE = GM_DRUM_NOTES["snare"]
_CLAP = GM_DRUM_NOTES["clap"]
_LOW_TOM = GM_DRUM_NOTES["low_tom"]
_MID_TOM = GM_DRUM_NOTES["mid_tom"]
_HIGH_TOM = GM_DRUM_NOTES["high_tom"]
_CLOSED_HAT = GM_DRUM_NOTES["closed_hat"]
_OPEN_HAT = GM_DRUM_NOTES["open_hat"]
_CRASH = GM_DRUM_NOTES["crash"]


def _clamp(value: int, low: int = 1, high: int = 127) -> int:
    return max(low, min(high, value))


def _hat_8ths(velocity_strong: int = 84, velocity_weak: int = 70) -> list[DrumHit]:
    return [
        DrumHit(beat, 0.15, _CLOSED_HAT, _clamp(velocity_strong if i % 2 == 0 else velocity_weak), "hat")
        for i, beat in enumerate((0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5))
    ]


def _hat_16ths(intensity: float) -> list[DrumHit]:
    if intensity < 0.75:
        return []
    return [
        DrumHit(0.25 + i * 0.5, 0.1, _CLOSED_HAT, _clamp(66 if i % 2 == 0 else 58), "hat16")
        for i in range(8)
    ]


def pop_groove(intensity: float = 0.6) -> list[DrumHit]:
    """流行鼓：kick 1/3（高强时 3&），snare 2/4，八分踩镲，高强开镲。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 104, "kick"),
        DrumHit(2.0, 0.4, _KICK, 96, "kick"),
        DrumHit(1.0, 0.4, _SNARE, 104, "snare"),
        DrumHit(3.0, 0.4, _SNARE, 100, "snare"),
        *_hat_8ths(),
    ]
    if intensity >= 0.75:
        hits.append(DrumHit(2.5, 0.2, _KICK, 82, "kick3and"))
    if intensity >= 0.7:
        hits.append(DrumHit(1.5, 0.2, _OPEN_HAT, 88, "open_hat"))
    hits.extend(_hat_16ths(intensity))
    return hits


def rock_groove(intensity: float = 0.6) -> list[DrumHit]:
    """摇滚鼓：kick 1/3/3&，snare 2/4，八分踩镲。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 106, "kick"),
        DrumHit(1.0, 0.2, _KICK, 84, "kick"),
        DrumHit(2.0, 0.4, _KICK, 100, "kick"),
        DrumHit(2.5, 0.2, _KICK, 88, "kick3and"),
        DrumHit(3.0, 0.2, _KICK, 82, "kick4"),
        DrumHit(1.0, 0.4, _SNARE, 106, "snare"),
        DrumHit(3.0, 0.4, _SNARE, 104, "snare"),
        *_hat_8ths(86, 74),
    ]
    hits.extend(_hat_16ths(intensity))
    return hits


def lo_fi_groove(intensity: float = 0.6) -> list[DrumHit]:
    """Lo-fi 鼓：syncopated kick、snare/clap 2/4、ghost snare、swing 由引擎应用。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 96, "kick"),
        DrumHit(2.5, 0.3, _KICK, 84, "kick"),
        DrumHit(3.75, 0.25, _KICK, 78, "kickSync"),
        DrumHit(1.0, 0.4, _CLAP, 92, "clap"),
        DrumHit(3.0, 0.4, _SNARE, 90, "snare"),
        # ghost snare：轻力度装饰
        DrumHit(1.5, 0.2, _SNARE, 32, "ghost"),
        DrumHit(2.75, 0.2, _SNARE, 30, "ghost"),
        *_hat_8ths(72, 58),
    ]
    hits.extend(_hat_16ths(intensity))
    return hits


def cinematic_groove(intensity: float = 0.6) -> list[DrumHit]:
    """电影感鼓：稀疏低频 + 撞击 + tom。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.5, _KICK, 102, "kick"),
        DrumHit(2.5, 0.3, _KICK, 88, "kick"),
        DrumHit(0.0, 0.3, _CRASH, 92, "crash"),
    ]
    if intensity >= 0.7:
        hits.append(DrumHit(1.0, 0.4, _LOW_TOM, 84, "tom"))
        hits.append(DrumHit(3.0, 0.4, _MID_TOM, 82, "tom"))
    return hits


def chinese_groove(intensity: float = 0.6) -> list[DrumHit]:
    """中国风鼓：tom 模拟民族鼓氛围，节奏稳定，高强时推进。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 96, "kick"),
        DrumHit(2.0, 0.4, _KICK, 88, "kick"),
        DrumHit(0.0, 0.4, _LOW_TOM, 86, "tom"),
        DrumHit(1.5, 0.3, _MID_TOM, 80, "tom"),
        DrumHit(2.5, 0.3, _MID_TOM, 80, "tom"),
        DrumHit(3.5, 0.4, _LOW_TOM, 84, "tom"),
    ]
    if intensity >= 0.8:
        hits.append(DrumHit(3.0, 0.4, _SNARE, 92, "snare"))
    return hits


def electronic_groove(intensity: float = 0.6) -> list[DrumHit]:
    """电子鼓：four-on-the-floor、clap 2/4、offbeat 十六分踩镲。"""
    hits: list[DrumHit] = [
        DrumHit(beat, 0.25, _KICK, 104 if beat in (0.0, 2.0) else 92, "kick")
        for beat in (0.0, 1.0, 2.0, 3.0)
    ]
    hits.extend([DrumHit(1.0, 0.2, _CLAP, 98, "clap"), DrumHit(3.0, 0.2, _CLAP, 96, "clap")])
    hits.extend(
        [
            DrumHit(0.25 + i * 0.5, 0.1, _CLOSED_HAT, _clamp(70 if i % 2 == 0 else 60), "hat16")
            for i in range(8)
        ]
    )
    return hits


def four_on_floor_groove(intensity: float = 0.6) -> list[DrumHit]:
    """四踩鼓：kick 每拍、snare/clap 2/4、八分踩镲。"""
    hits: list[DrumHit] = [
        DrumHit(beat, 0.25, _KICK, 102 if beat in (0.0, 2.0) else 90, "kick")
        for beat in (0.0, 1.0, 2.0, 3.0)
    ]
    hits.extend([DrumHit(1.0, 0.4, _SNARE, 100, "snare"), DrumHit(3.0, 0.4, _SNARE, 96, "snare")])
    hits.extend(_hat_8ths(80, 66))
    if intensity >= 0.7:
        hits.append(DrumHit(2.5, 0.2, _OPEN_HAT, 84, "open_hat"))
    hits.extend(_hat_16ths(intensity))
    return hits


def rock_backbeat_groove(intensity: float = 0.6) -> list[DrumHit]:
    """摇滚 backbeat：强 snare 2/4、kick 1/3/3&、八分踩镲密集。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 108, "kick"),
        DrumHit(1.0, 0.2, _KICK, 88, "kick"),
        DrumHit(2.0, 0.4, _KICK, 102, "kick"),
        DrumHit(2.5, 0.2, _KICK, 90, "kick3and"),
        DrumHit(1.0, 0.4, _SNARE, 110, "snare"),
        DrumHit(3.0, 0.4, _SNARE, 108, "snare"),
        *_hat_8ths(90, 76),
    ]
    if intensity >= 0.8:
        hits.append(DrumHit(0.0, 0.3, _CRASH, 96, "crash"))
    hits.extend(_hat_16ths(intensity))
    return hits


def battle_drive_groove(intensity: float = 0.6) -> list[DrumHit]:
    """战斗推进鼓：高密度 kick + snare 与 tom，适合高速游戏战斗。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.2, _KICK, 112, "kick"),
        DrumHit(0.75, 0.2, _KICK, 92, "kick"),
        DrumHit(1.5, 0.2, _KICK, 96, "kick"),
        DrumHit(2.0, 0.2, _KICK, 108, "kick"),
        DrumHit(2.75, 0.2, _KICK, 92, "kick"),
        DrumHit(3.5, 0.2, _KICK, 96, "kick"),
        DrumHit(1.0, 0.2, _SNARE, 106, "snare"),
        DrumHit(3.0, 0.2, _SNARE, 104, "snare"),
        DrumHit(0.0, 0.2, _CRASH, 98, "crash"),
    ]
    if intensity >= 0.7:
        hits.extend(
            [
                DrumHit(0.5, 0.2, _MID_TOM, 84, "tom"),
                DrumHit(1.5, 0.2, _LOW_TOM, 82, "tom"),
                DrumHit(2.5, 0.2, _MID_TOM, 84, "tom"),
            ]
        )
    hits.extend(_hat_16ths(intensity))
    return hits


def ambient_minimal_groove(intensity: float = 0.6) -> list[DrumHit]:
    """氛围极简鼓：几乎无强鼓点，仅轻 kick / hat。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.5, _KICK, 72, "kick"),
        DrumHit(0.0, 0.2, _CLOSED_HAT, 58, "hat"),
        DrumHit(2.0, 0.3, _CLOSED_HAT, 54, "hat"),
    ]
    if intensity >= 0.6:
        hits.append(DrumHit(2.0, 0.5, _KICK, 66, "kick"))
    return hits


def cinematic_taiko_groove(intensity: float = 0.6) -> list[DrumHit]:
    """影视/民族 taiko：低频撞击 + tom，稀疏但有重量。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.6, _KICK, 104, "kick"),
        DrumHit(2.5, 0.4, _KICK, 90, "kick"),
        DrumHit(0.0, 0.4, _LOW_TOM, 88, "tom"),
        DrumHit(1.5, 0.3, _MID_TOM, 82, "tom"),
        DrumHit(2.5, 0.3, _MID_TOM, 82, "tom"),
    ]
    if intensity >= 0.75:
        hits.append(DrumHit(3.5, 0.4, _LOW_TOM, 86, "tom"))
    return hits


def funk_groove(intensity: float = 0.6) -> list[DrumHit]:
    """Funk：syncopated kick、ghost snare、强 offbeat。"""
    hits: list[DrumHit] = [
        DrumHit(0.0, 0.4, _KICK, 98, "kick"),
        DrumHit(2.25, 0.3, _KICK, 88, "kick"),
        DrumHit(3.5, 0.3, _KICK, 84, "kick"),
        DrumHit(1.0, 0.3, _SNARE, 100, "snare"),
        DrumHit(3.0, 0.3, _SNARE, 96, "snare"),
        DrumHit(0.75, 0.2, _SNARE, 34, "ghost"),
        DrumHit(2.75, 0.2, _SNARE, 32, "ghost"),
        *_hat_8ths(86, 70),
    ]
    if intensity >= 0.7:
        hits.append(DrumHit(1.75, 0.2, _OPEN_HAT, 88, "open_hat"))
    return hits


GROOVE_BUILDERS = {
    "pop": pop_groove,
    "rock": rock_groove,
    "lo-fi": lo_fi_groove,
    "cinematic": cinematic_groove,
    "chinese": chinese_groove,
    "electronic": electronic_groove,
    "four_on_floor": four_on_floor_groove,
    "lofi_swing": lo_fi_groove,
    "rock_backbeat": rock_backbeat_groove,
    "battle_drive": battle_drive_groove,
    "ambient_minimal": ambient_minimal_groove,
    "cinematic_taiko": cinematic_taiko_groove,
    "funk_groove": funk_groove,
}


def build_fill(style: str, rng: random.Random) -> list[DrumHit]:
    """轻量 fill：覆盖小节最后 1 拍，不越界、密度适中。"""
    if style == "rock":
        notes = [_MID_TOM, _HIGH_TOM, _MID_TOM, _LOW_TOM]
    elif style in ("cinematic", "chinese"):
        notes = [_LOW_TOM, _MID_TOM, _LOW_TOM, _MID_TOM]
    elif style == "lo-fi":
        notes = [_CLOSED_HAT, _CLOSED_HAT, _SNARE, _OPEN_HAT]
    elif style == "electronic":
        notes = [_SNARE, _SNARE, _SNARE, _CRASH]
    else:  # pop / 默认：snare 16th fill
        notes = [_SNARE, _SNARE, _SNARE, _SNARE]
    start = 3.0
    hits: list[DrumHit] = []
    for i, note in enumerate(notes):
        hits.append(
            DrumHit(
                round(start + i * 0.25, 3),
                0.2,
                note,
                _clamp(92 + rng.randrange(0, 9)),
                "fill",
            )
        )
    return hits
