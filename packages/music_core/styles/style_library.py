"""内置风格模板库。"""

from __future__ import annotations

from packages.music_core.styles.style_models import StyleTemplateSpec


def _default_form() -> list[dict]:
    return [
        {"id": "intro", "name": "前奏", "start_bar": 1, "bars": 4, "energy": 0.2},
        {"id": "verse", "name": "主歌", "start_bar": 5, "bars": 8, "energy": 0.5},
        {"id": "chorus", "name": "副歌", "start_bar": 13, "bars": 16, "energy": 0.9},
        {"id": "outro", "name": "尾奏", "start_bar": 29, "bars": 4, "energy": 0.3},
    ]


_TEMPLATES: list[StyleTemplateSpec] = [
    StyleTemplateSpec(
        id="cinematic_piano",
        name="电影感钢琴",
        description="电影感钢琴配乐：慢速、小调、钢琴 + 弦乐 + pad，动态大",
        tags=["cinematic", "piano", "slow", "minor"],
        default_tempo=72,
        tempo_range=(60, 90),
        preferred_modes=["minor", "natural_minor"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "acoustic_grand_piano", "pattern": "legato"},
            {"id": "piano", "role": "harmony", "instrument": "acoustic_grand_piano", "pattern": "arpeggio"},
            {"id": "strings", "role": "pad", "instrument": "string_ensemble_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["Dm", "Bb", "F", "C"], ["Dm", "Bb", "C", "Dm"]],
        rhythm_presets=["arpeggio", "sustained_pad"],
        melody_profile={"density": 0.45, "range": "mid-high", "energy_boost": 0.6},
        arrangement_curve={"intro": 0.2, "verse": 0.5, "chorus": 0.9, "outro": 0.25, "dynamic": "wide"},
        mix_hints={"pad_volume": 0.7, "piano_volume": 1.0},
        soundfont_hint="cinematic_piano",
        preferred_soundfont_tags=["strings", "piano"],
        notes="慢速电影感钢琴配乐模板",
    ),
    StyleTemplateSpec(
        id="lo_fi_hiphop",
        name="Lo-fi Hiphop",
        description="Lo-fi：慢中速、鼓 + 贝斯 + 电钢 + pad，松散律动",
        tags=["lo-fi", "hiphop", "chill"],
        default_tempo=82,
        tempo_range=(70, 95),
        preferred_modes=["major", "dorian"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "electric_piano_1", "pattern": "legato"},
            {"id": "piano", "role": "harmony", "instrument": "electric_piano_1", "pattern": "broken_chords"},
            {"id": "bass", "role": "bass", "instrument": "electric_bass_finger", "pattern": "roots"},
            {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "pattern": "lo-fi"},
            {"id": "pad", "role": "pad", "instrument": "string_ensemble_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["C", "G", "Am", "F"], ["Am7", "Dm7", "G7", "Cmaj7"]],
        rhythm_presets=["lo-fi", "broken_chords"],
        melody_profile={"density": 0.4, "range": "mid", "energy_boost": 0.3},
        arrangement_curve={"intro": 0.25, "verse": 0.5, "chorus": 0.7, "outro": 0.3},
        soundfont_hint="lofi",
        preferred_soundfont_tags=["warm", "vintage"],
        notes="Lo-fi hiphop 模板",
    ),
    StyleTemplateSpec(
        id="pop_ballad",
        name="流行情歌",
        description="流行情歌：中速、钢琴/吉他 + 贝斯 + 鼓 + 弦乐，副歌明显增强",
        tags=["pop", "ballad", "major"],
        default_tempo=96,
        tempo_range=(80, 112),
        preferred_modes=["major"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "lead_1_square", "pattern": "legato"},
            {"id": "piano", "role": "harmony", "instrument": "acoustic_grand_piano", "pattern": "block_chords"},
            {"id": "bass", "role": "bass", "instrument": "electric_bass_finger", "pattern": "roots"},
            {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "pattern": "pop"},
            {"id": "strings", "role": "pad", "instrument": "string_ensemble_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["C", "G", "Am", "F"], ["F", "G", "C", "C"]],
        rhythm_presets=["pop", "block_chords"],
        melody_profile={"density": 0.55, "range": "mid-high", "energy_boost": 0.7},
        arrangement_curve={"intro": 0.2, "verse": 0.5, "chorus": 1.0, "outro": 0.3, "chorus_boost": True},
        preferred_soundfont_tags=["piano", "strings"],
        notes="流行情歌模板",
    ),
    StyleTemplateSpec(
        id="chinese_cinematic",
        name="中国风电影配乐",
        description="中国风电影配乐：五声音阶、弦乐 + 古筝替代音色 + pad",
        tags=["chinese", "cinematic", "pentatonic"],
        default_tempo=76,
        tempo_range=(64, 92),
        preferred_modes=["pentatonic", "minor_pentatonic"],
        preferred_scales=["major_pentatonic", "minor_pentatonic"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "violin", "pattern": "legato"},
            {"id": "piano", "role": "harmony", "instrument": "acoustic_grand_piano", "pattern": "arpeggio"},
            {"id": "strings", "role": "pad", "instrument": "string_ensemble_1", "pattern": "sustained_pad"},
            {"id": "pad", "role": "pad", "instrument": "synth_strings_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["Dm", "C", "Bb", "Dm"], ["Am", "G", "F", "Am"]],
        rhythm_presets=["arpeggio", "sustained_pad"],
        melody_profile={"density": 0.4, "range": "mid-high", "energy_boost": 0.5},
        arrangement_curve={"intro": 0.2, "verse": 0.5, "chorus": 0.85, "outro": 0.25},
        soundfont_hint="chinese",
        preferred_soundfont_tags=["ethnic", "orchestral"],
        notes="中国风五声音阶模板",
    ),
    StyleTemplateSpec(
        id="game_battle",
        name="游戏战斗",
        description="游戏战斗音乐：快速、高能量、鼓 + 低音 + 弦乐 + 铜管替代",
        tags=["game", "battle", "fast", "high-energy"],
        default_tempo=150,
        tempo_range=(130, 180),
        preferred_modes=["minor"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "lead_1_square", "pattern": "staccato"},
            {"id": "piano", "role": "harmony", "instrument": "electric_guitar_clean", "pattern": "block_chords"},
            {"id": "bass", "role": "bass", "instrument": "synth_bass_1", "pattern": "roots"},
            {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "pattern": "rock"},
            {"id": "strings", "role": "pad", "instrument": "string_ensemble_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["Dm", "Bb", "C", "Dm"], ["Am", "F", "G", "Am"]],
        rhythm_presets=["rock", "electronic"],
        melody_profile={"density": 0.75, "range": "high", "energy_boost": 1.0},
        arrangement_curve={"intro": 0.4, "verse": 0.7, "chorus": 1.0, "outro": 0.4, "dynamic": "intense"},
        preferred_soundfont_tags=["orchestral", "band"],
        notes="游戏战斗模板",
    ),
    StyleTemplateSpec(
        id="ambient_meditation",
        name="冥想氛围",
        description="冥想氛围：慢速、pad 长音、极低密度旋律",
        tags=["ambient", "meditation", "slow", "sparse"],
        default_tempo=60,
        tempo_range=(50, 72),
        preferred_modes=["major", "dorian"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "pad_2_warm", "pattern": "sustained_pad"},
            {"id": "pad", "role": "pad", "instrument": "pad_2_warm", "pattern": "sustained_pad"},
            {"id": "strings", "role": "pad", "instrument": "synth_strings_1", "pattern": "sustained_pad"},
        ],
        harmony_presets=[["C", "Am", "F", "G"], ["Dm", "C", "Bb", "C"]],
        rhythm_presets=["sustained_pad"],
        melody_profile={"density": 0.15, "range": "mid", "energy_boost": 0.1},
        arrangement_curve={"intro": 0.1, "verse": 0.35, "chorus": 0.5, "outro": 0.1, "dynamic": "calm"},
        soundfont_hint="meditation",
        preferred_soundfont_tags=["warm", "pad"],
        notes="冥想氛围模板",
    ),
    StyleTemplateSpec(
        id="electronic_pulse",
        name="电子律动",
        description="电子律动：中高速、synth + bass + drums + arpeggio",
        tags=["electronic", "synth", "dance"],
        default_tempo=124,
        tempo_range=(112, 140),
        preferred_modes=["minor"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "lead_1_square", "pattern": "legato"},
            {"id": "piano", "role": "harmony", "instrument": "pad_2_warm", "pattern": "arpeggio"},
            {"id": "bass", "role": "bass", "instrument": "synth_bass_1", "pattern": "roots"},
            {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "pattern": "electronic"},
        ],
        harmony_presets=[["Am", "F", "C", "G"], ["Dm", "Bb", "F", "C"]],
        rhythm_presets=["electronic", "arpeggio"],
        melody_profile={"density": 0.7, "range": "mid-high", "energy_boost": 0.8},
        arrangement_curve={"intro": 0.3, "verse": 0.6, "chorus": 1.0, "outro": 0.3},
        preferred_soundfont_tags=["synth", "electronic"],
        notes="电子律动模板",
    ),
    StyleTemplateSpec(
        id="rock_theme",
        name="摇滚主题",
        description="摇滚主题：鼓 + 贝斯 + 电吉他 + 强节奏",
        tags=["rock", "guitar", "strong-rhythm"],
        default_tempo=132,
        tempo_range=(112, 156),
        preferred_modes=["major", "minor"],
        default_length_bars=32,
        default_form=_default_form(),
        default_tracks=[
            {"id": "melody", "role": "melody", "instrument": "electric_guitar_clean", "pattern": "riff"},
            {"id": "piano", "role": "harmony", "instrument": "electric_guitar_clean", "pattern": "block_chords"},
            {"id": "bass", "role": "bass", "instrument": "electric_bass_finger", "pattern": "roots"},
            {"id": "drums", "role": "drums", "instrument": "standard_drum_kit", "pattern": "rock"},
        ],
        harmony_presets=[["C", "G", "Am", "F"], ["E", "C", "G", "D"]],
        rhythm_presets=["rock"],
        melody_profile={"density": 0.65, "range": "mid-high", "energy_boost": 0.9},
        arrangement_curve={"intro": 0.3, "verse": 0.65, "chorus": 1.0, "outro": 0.35},
        soundfont_hint="rock",
        preferred_soundfont_tags=["electric-guitar", "band"],
        notes="摇滚主题模板",
    ),
]


def list_style_templates() -> list[StyleTemplateSpec]:
    """返回全部内置风格模板。"""
    return list(_TEMPLATES)


def get_style_template(template_id: str) -> StyleTemplateSpec:
    """按 id 获取模板；不存在抛 ValueError。"""
    for template in _TEMPLATES:
        if template.id == template_id:
            return template
    raise ValueError(f"风格模板不存在：{template_id}")


def find_style_templates(
    query: str | None = None,
    tags: list[str] | None = None,
) -> list[StyleTemplateSpec]:
    """按 id / name / tag 模糊匹配。"""
    results = list(_TEMPLATES)
    if tags:
        tag_set = {t.lower() for t in tags}
        results = [t for t in results if any(tag in {x.lower() for x in t.tags} for tag in tag_set)]
    if query:
        q = query.lower()
        results = [
            t
            for t in results
            if q in t.id.lower()
            or q in t.name.lower()
            or q in " ".join(t.tags).lower()
            or q in t.description.lower()
        ]
    return results
