"""和弦 Voicing（T22）：按 register 生成适合 strings / pad 的和弦排列。"""

from __future__ import annotations

from packages.music_core.theory.chords import chord_symbol_to_pitches


def _chord_tones_in_register(chord_symbol: str, register: tuple[int, int]) -> list[int]:
    """返回和弦音在 register 内的全部候选音高。"""
    low, high = register
    pitches = chord_symbol_to_pitches(chord_symbol, octave=4)
    tones: list[int] = []
    for pitch in pitches:
        for octave_shift in range(-4, 4):
            candidate = pitch + 12 * octave_shift
            if low <= candidate <= high:
                tones.append(candidate)
    return sorted(set(tones))


def build_chord_voicing(
    chord_symbol: str,
    *,
    register: tuple[int, int],
    previous_voicing: list[int] | None = None,
    max_voice_movement: int = 7,
    voice_count: int = 3,
) -> list[int]:
    """生成 chord voicing（3-4 声部，低到高排序，优先 chord tones）。

    非法和弦不崩溃：chord parser 回退 C major，返回可用的 C major voicing。
    """
    low, high = register
    tones = _chord_tones_in_register(chord_symbol, register)
    if not tones:
        tones = [36, 40, 43]

    if previous_voicing:
        # 每个 previous voice 找最近 chord tone（保持共同音 / 小移动）
        assigned: list[int] = []
        for previous in previous_voicing:
            nearest = min(tones, key=lambda tone: abs(tone - previous))
            assigned.append(nearest)
        # 去重：重复音上移八度（仍在 register 内）
        unique: list[int] = []
        seen: set[int] = set()
        for pitch in sorted(assigned):
            candidate = pitch
            while candidate in seen and candidate + 12 <= high:
                candidate += 12
            if candidate not in seen:
                seen.add(candidate)
                unique.append(candidate)
        # 补足声部
        remaining = [t for t in tones if t not in seen]
        while len(unique) < voice_count and remaining:
            unique.append(remaining.pop(0))
        voicing = sorted(unique)[:voice_count]
    else:
        # 每个 pitch class 取一个代表，覆盖不同和弦音，再按步长扩展
        by_pc: dict[int, int] = {}
        for tone in tones:
            by_pc.setdefault(tone % 12, tone)
        representatives = sorted(by_pc.values())
        if len(representatives) >= voice_count:
            step = max(1, len(representatives) // voice_count)
            voicing = sorted(representatives[i] for i in range(0, len(representatives), step))[:voice_count]
        else:
            voicing = representatives

    # 兜底：声部不足时补低音八度
    if len(voicing) < voice_count:
        filler = [t + 12 for t in voicing if t + 12 <= high]
        voicing = sorted(set(voicing + filler))[:voice_count]
    if not voicing:
        voicing = [max(low, 48), max(low, 52), max(low, 55)]
    return [max(low, min(high, pitch)) for pitch in sorted(voicing)]
