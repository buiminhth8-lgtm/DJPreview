"""贝斯 groove 模式库（T21）：风格化 bassline + root/fifth/octave/passing/approach。"""

from __future__ import annotations

import random

from packages.music_core.composer.bass_models import BassNote
from packages.music_core.theory.chords import chord_symbol_to_pitches

BASS_MIN = 36
BASS_MAX = 52


def _clamp(value: int, low: int = 1, high: int = 127) -> int:
    return max(low, min(high, value))


def get_chord_root_pitch(
    chord_symbol: str,
    key: str | None = None,
    bass_range: tuple[int, int] = (BASS_MIN, BASS_MAX),
) -> int:
    """取和弦根音并放到低音区最低可用八度。"""
    pitches = chord_symbol_to_pitches(chord_symbol, octave=4)
    root = pitches[0] if pitches else 60
    while root - 12 >= bass_range[0]:
        root -= 12
    return _clamp(root, bass_range[0], bass_range[1])


def get_bass_chord_tones(
    chord_symbol: str,
    bass_range: tuple[int, int] = (BASS_MIN, BASS_MAX),
) -> list[int]:
    """返回和弦音在低音区内的全部候选音高。"""
    pitches = chord_symbol_to_pitches(chord_symbol, octave=4)
    tones: list[int] = []
    for pitch in pitches:
        for octave_shift in range(-3, 4):
            candidate = pitch + 12 * octave_shift
            if bass_range[0] <= candidate <= bass_range[1]:
                tones.append(candidate)
    return sorted(set(tones))


def choose_passing_tone(from_pitch: int, to_pitch: int, scale_pitches: set[int]) -> int | None:
    """在 from/to 之间选择最近的调内经过音。"""
    if not scale_pitches:
        return None
    mid = (from_pitch + to_pitch) // 2
    return min(scale_pitches, key=lambda p: abs(p - mid))


def _bass_parts(root: int, fifth: int, octave: int) -> tuple[int, int, int]:
    return root, fifth, octave


def pop_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """流行贝斯：root/fifth/octave，跟随 kick（1/3 拍）。"""
    hits: list[BassNote] = [
        BassNote(0.0, 1.4, root, 94, "root"),
        BassNote(2.0, 1.2, root, 86, "root"),
    ]
    if intensity >= 0.55:
        hits.append(BassNote(1.0, 0.5, fifth, 74, "fifth"))
    if intensity >= 0.8:
        hits.append(BassNote(3.0, 0.5, octave if rng.random() < 0.6 else fifth, 80, "octave"))
    return hits


def rock_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """摇滚贝斯：8 分音符 driving，root/fifth 交替，与 kick 强同步。"""
    hits: list[BassNote] = []
    for i, beat in enumerate((0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)):
        use_fifth = i in (1, 5) or (i == 7 and rng.random() < 0.5)
        hits.append(
            BassNote(
                beat,
                0.4,
                fifth if use_fifth else root,
                96 if beat in (0.0, 2.0) else (80 if i % 2 == 0 else 72),
                "fifth" if use_fifth else "root",
            )
        )
    return hits


def lo_fi_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """Lo-fi 贝斯：syncopated 短句 + approach，音符短而松弛（swing 由引擎应用）。"""
    hits: list[BassNote] = [
        BassNote(0.0, 0.8, root, 84, "root"),
        BassNote(1.5, 0.5, fifth, 70, "fifth"),
        BassNote(2.5, 0.7, root, 80, "root"),
        BassNote(3.75, 0.4, fifth if rng.random() < 0.5 else root, 66, "ghost"),
    ]
    if intensity >= 0.75:
        hits.append(BassNote(3.0, 0.4, octave, 78, "octave"))
    return hits


def cinematic_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """影视贝斯：低频长音为主，少量 octave movement。"""
    hits: list[BassNote] = [BassNote(0.0, 3.6, root, 88, "root")]
    if intensity >= 0.7:
        hits.append(BassNote(2.0, 1.0, fifth, 76, "fifth"))
    if intensity >= 0.85 and rng.random() < 0.5:
        hits.append(BassNote(1.0, 0.6, octave, 74, "octave"))
    return hits


def chinese_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """中国风贝斯：稳定根音/五度，节奏稳重，与低鼓呼应。"""
    hits: list[BassNote] = [
        BassNote(0.0, 1.6, root, 90, "root"),
        BassNote(2.0, 1.6, root, 82, "root"),
    ]
    if intensity >= 0.6:
        hits.append(BassNote(1.0, 0.6, fifth, 72, "fifth"))
    if intensity >= 0.85:
        hits.append(BassNote(3.0, 0.6, fifth, 76, "fifth"))
    return hits


def electronic_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """电子贝斯：offbeat 插入 kick 之间，root 聚焦。"""
    hits: list[BassNote] = [
        BassNote(0.5, 0.35, root, 90, "root"),
        BassNote(1.5, 0.35, root, 84, "root"),
        BassNote(2.5, 0.35, root, 90, "root"),
        BassNote(3.5, 0.35, fifth if rng.random() < 0.5 else root, 78, "fifth"),
    ]
    return hits


def laidback_groove_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """松弛律动贝斯：低密度、长根音 + 少量 syncopation，适合 lo-fi。"""
    hits: list[BassNote] = [
        BassNote(0.0, 1.6, root, 84, "root"),
        BassNote(2.5, 1.0, root, 78, "root"),
        BassNote(3.75, 0.5, fifth if rng.random() < 0.5 else root, 66, "ghost"),
    ]
    if intensity >= 0.75:
        hits.append(BassNote(1.5, 0.5, fifth, 72, "fifth"))
    return hits


def root_fifth_drive_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """根音/五度推进：强拍 root、次强拍 fifth，八分运动，适合 pop/rock。"""
    hits: list[BassNote] = [
        BassNote(beat, 0.7 if i % 2 == 0 else 0.4, root if i % 2 == 0 else fifth, 88 if i % 2 == 0 else 76, "drive")
        for i, beat in enumerate((0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5))
    ]
    if intensity >= 0.8:
        hits.append(BassNote(1.75, 0.3, octave, 82, "octave"))
    return hits


def driving_octaves_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """八度推进贝斯：root/octave 交替，16 分能量感，适合 game/electronic。"""
    hits: list[BassNote] = [
        BassNote(beat, 0.35, root if i % 2 == 0 else octave, 96 if i % 2 == 0 else 86, "octave_drive")
        for i, beat in enumerate((0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5))
    ]
    if intensity >= 0.8:
        hits.extend(
            [
                BassNote(0.25, 0.25, root, 82, "ghost"),
                BassNote(1.25, 0.25, fifth, 78, "ghost"),
                BassNote(2.25, 0.25, root, 82, "ghost"),
                BassNote(3.25, 0.25, octave, 80, "ghost"),
            ]
        )
    return hits


def funk_bass(root: int, fifth: int, octave: int, intensity: float, rng: random.Random) -> list[BassNote]:
    """Funk 贝斯：syncopated 短句 + octave 弹跳。"""
    hits: list[BassNote] = [
        BassNote(0.0, 0.6, root, 90, "root"),
        BassNote(1.5, 0.5, fifth, 78, "fifth"),
        BassNote(2.25, 0.5, root, 86, "root"),
        BassNote(3.5, 0.5, octave, 84, "octave"),
    ]
    if intensity >= 0.7:
        hits.append(BassNote(0.75, 0.3, root, 74, "ghost"))
        hits.append(BassNote(2.75, 0.3, fifth, 72, "ghost"))
    return hits


BASS_GROOVES = {
    "pop": pop_bass,
    "rock": rock_bass,
    "lo-fi": lo_fi_bass,
    "cinematic": cinematic_bass,
    "chinese": chinese_bass,
    "electronic": electronic_bass,
    "laidback_groove": laidback_groove_bass,
    "root_fifth_drive": root_fifth_drive_bass,
    "driving_octaves": driving_octaves_bass,
    "funk_groove": funk_bass,
}


def bass_style_swing(style: str) -> float:
    """贝斯风格 swing（lo-fi 明显）。"""
    return 0.62 if style in ("lo-fi", "hiphop", "laidback_groove", "funk_groove") else 0.5


def implied_kick_positions(style: str) -> list[float]:
    """风格隐含的主要 kick 拍位（与 DrumEngine 的 groove 一致）。"""
    if style == "rock":
        return [0.0, 1.0, 2.0, 2.5, 3.0]
    if style == "lo-fi":
        return [0.0, 2.5, 3.75]
    if style in ("cinematic", "chinese"):
        return [0.0, 2.0]
    if style == "electronic":
        return [0.0, 1.0, 2.0, 3.0]
    return [0.0, 2.0]


def build_approach_note(to_pitch: int, scale_pitches: set[int]) -> int | None:
    """到目标音的 approach note：目标下方最近的调内音。"""
    if not scale_pitches:
        return None
    below = [p for p in scale_pitches if p < to_pitch]
    return max(below) if below else None
