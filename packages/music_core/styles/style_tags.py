"""风格标签归一化：避免大量 prompt / 模板 fallback 到 pop。"""

from __future__ import annotations

_ALIASES: dict[str, set[str]] = {
    "lofi": {"lofi", "lo-fi", "lo_fi", "lo fi"},
    "hiphop": {"hiphop", "hip-hop", "hip hop", "chillhop"},
    "rock": {"rock", "摇滚", "hard rock", "punk"},
    "game": {"game", "battle", "boss", "战斗", "游戏"},
    "cinematic": {"cinematic", "电影", "影视", "score", "配乐"},
    "chinese": {"chinese", "中国风", "oriental", "东方", "民族"},
    "ambient": {"ambient", "meditation", "冥想", "氛围", "sparse", "atmospheric"},
    "electronic": {"electronic", "edm", "电子", "synth", "dance", "pulse"},
    "pop": {"pop", "ballad", "情歌", "流行"},
}


def normalize_style_tags(style: list[str] | tuple[str, ...] | str | None) -> set[str]:
    """把 style 标签归一化为 canonical 集合（如 lofi / rock / game / cinematic...）。"""
    if style is None:
        return set()
    if isinstance(style, str):
        raw = [style]
    else:
        raw = list(style)
    text = " ".join(str(t).strip().lower() for t in raw if t)
    matched: set[str] = set()
    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            if alias in text:
                matched.add(canonical)
                break
    return matched
