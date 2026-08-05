"""T31：Melody / Drum / Bass 引擎消费 track.pattern 与风格标签。"""

from packages.music_core.bass.bass_engine import BassEngine
from packages.music_core.drums.drum_engine import DrumEngine
from packages.music_core.harmony.harmony_engine import build_bar_harmony
from packages.music_core.melody.melody_engine import MelodyEngine
from services.api.schemas.music_spec import MusicSpec
from tests.test_bass_engine import _spec as _bass_spec
from tests.test_drum_engine import _spec as _drum_spec


def _with_pattern(base: MusicSpec, role: str, pattern: str, style: list[str] | None = None) -> MusicSpec:
    spec = base.model_copy(deep=True)
    if style is not None:
        spec.style = style
    for track in spec.tracks:
        if track.role == role:
            track.pattern = pattern
    return spec


def test_drum_engine_uses_track_pattern():
    base = _drum_spec()
    lofi = _with_pattern(base, "drums", "lofi_swing", ["lo-fi"])
    rock = _with_pattern(base, "drums", "rock_backbeat", ["rock"])
    lofi_hits = {(round(n.start_beat, 2), n.pitch) for n in DrumEngine().generate(lofi, build_bar_harmony(lofi))}
    rock_hits = {(round(n.start_beat, 2), n.pitch) for n in DrumEngine().generate(rock, build_bar_harmony(rock))}
    assert lofi_hits != rock_hits
    # ambient_minimal 没有强 four-on-the-floor（每拍 kick）
    ambient = _with_pattern(base, "drums", "ambient_minimal", ["ambient"])
    ambient_hits = [round(n.start_beat, 2) for n in DrumEngine().generate(ambient, build_bar_harmony(ambient))]
    assert all(beat not in ambient_hits for beat in (1.0, 3.0))


def test_bass_engine_uses_track_pattern():
    base = _bass_spec()
    laidback = _with_pattern(base, "bass", "laidback_groove", ["lo-fi"])
    driving = _with_pattern(base, "bass", "driving_octaves", ["game"])
    laidback_onsets = [round(n.start_beat, 2) for n in BassEngine().generate(laidback, build_bar_harmony(laidback))]
    driving_onsets = [round(n.start_beat, 2) for n in BassEngine().generate(driving, build_bar_harmony(driving))]
    assert laidback_onsets != driving_onsets
    assert len(driving_onsets) > len(laidback_onsets)


def test_melody_engine_style_density_differs():
    base = _bass_spec()
    lo = _with_pattern(base, "melody", "legato", ["lo-fi"])
    game = _with_pattern(base, "melody", "staccato", ["game", "battle"])
    lo_notes = MelodyEngine().generate(lo, build_bar_harmony(lo), channel=0)
    game_notes = MelodyEngine().generate(game, build_bar_harmony(game), channel=0)
    assert lo_notes and game_notes
    assert len(game_notes) > len(lo_notes)
    lo_onsets = [round(n.start_beat, 1) for n in lo_notes[:8]]
    game_onsets = [round(n.start_beat, 1) for n in game_notes[:8]]
    assert lo_onsets != game_onsets
