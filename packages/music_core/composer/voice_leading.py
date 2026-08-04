"""Voice Leading（T22）：相邻和弦 voicing 平滑移动。"""

from __future__ import annotations

from packages.music_core.composer.voicing import build_chord_voicing


def smooth_voice_leading(
    chord_symbols: list[str],
    *,
    register: tuple[int, int],
    voice_count: int = 3,
    max_voice_movement: int = 7,
) -> list[list[int]]:
    """对连续和弦生成平滑 voicing 序列（输出长度与输入一致）。"""
    result: list[list[int]] = []
    previous: list[int] | None = None
    for symbol in chord_symbols:
        voicing = build_chord_voicing(
            symbol,
            register=register,
            previous_voicing=previous,
            max_voice_movement=max_voice_movement,
            voice_count=voice_count,
        )
        result.append(voicing)
        previous = voicing
    return result
