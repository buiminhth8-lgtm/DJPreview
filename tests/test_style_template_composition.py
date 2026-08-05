"""T31：风格模板驱动真实作曲差异（seed / tracks / harmony / melody / drums / bass）。"""

from fastapi.testclient import TestClient

from packages.music_core.composer.music_composer import compose_music
from packages.music_core.planner.music_planner import generate_music_spec_from_prompt
from packages.music_core.styles.style_applier import apply_style_template_to_music_spec
from packages.music_core.styles.style_library import get_style_template
from services.api.main import app

client = TestClient(app)


def _applied(template_id: str, strength: float = 0.7):
    base = generate_music_spec_from_prompt("生成一首测试音乐")
    return apply_style_template_to_music_spec(
        base.model_copy(deep=True), get_style_template(template_id), strength
    )


def _track(spec, role):
    return next((t for t in spec.tracks if t.role == role), None)


def test_different_templates_derive_different_seeds():
    lo = _applied("lo_fi_hiphop")
    rock = _applied("rock_theme")
    assert lo.seed != rock.seed
    # 可复现：同模板同强度结果稳定
    lo2 = _applied("lo_fi_hiphop")
    assert lo.seed == lo2.seed


def test_style_applier_overrides_existing_tracks():
    lo = _applied("lo_fi_hiphop")
    melody = _track(lo, "melody")
    assert melody is not None and melody.instrument == "electric_piano_1"
    assert melody.pattern == "legato"
    drums = _track(lo, "drums")
    assert drums is not None and drums.pattern == "lofi_swing"
    bass = _track(lo, "bass")
    assert bass is not None and bass.pattern == "laidback_groove"


def test_template_drum_patterns():
    assert _track(_applied("lo_fi_hiphop"), "drums").pattern == "lofi_swing"
    assert _track(_applied("game_battle"), "drums").pattern == "battle_drive"
    assert _track(_applied("rock_theme"), "drums").pattern == "rock_backbeat"
    # ambient 不是强 four_on_floor
    assert _track(_applied("ambient_meditation"), "drums").pattern == "ambient_minimal"


def test_harmony_presets_written_to_spec():
    lo = _applied("lo_fi_hiphop")
    battle = _applied("game_battle")
    verse_lo = next(h.progression for h in lo.harmony if h.section == "verse")
    verse_battle = next(h.progression for h in battle.harmony if h.section == "verse")
    assert verse_lo != verse_battle
    assert len(verse_lo) >= 4
    # 与模板 preset 一致
    assert verse_lo[:2] == get_style_template("lo_fi_hiphop").harmony_presets[0][:2]


def test_melody_differs_between_lofi_and_game():
    lo_spec = _applied("lo_fi_hiphop")
    game_spec = _applied("game_battle")
    lo_notes = [n for t in compose_music(lo_spec).tracks if t.role == "melody" for n in t.notes]
    game_notes = [n for t in compose_music(game_spec).tracks if t.role == "melody" for n in t.notes]
    assert lo_notes and game_notes
    lo_onsets = [round(n.start_beat, 1) for n in lo_notes[:8]]
    game_onsets = [round(n.start_beat, 1) for n in game_notes[:8]]
    assert lo_onsets != game_onsets
    # game 密度更高（音符数明显更多）
    assert len(game_notes) > len(lo_notes)


def test_drum_hits_differ_between_lofi_and_rock():
    from packages.music_core.drums.drum_engine import DrumEngine
    from packages.music_core.harmony.harmony_engine import build_bar_harmony

    lo = _applied("lo_fi_hiphop")
    rock = _applied("rock_theme")
    lo_hits = {(round(n.start_beat, 2), n.pitch) for n in DrumEngine().generate(lo, build_bar_harmony(lo))}
    rock_hits = {(round(n.start_beat, 2), n.pitch) for n in DrumEngine().generate(rock, build_bar_harmony(rock))}
    assert lo_hits != rock_hits


def test_bass_rhythm_differs_between_laidback_and_driving():
    from packages.music_core.bass.bass_engine import BassEngine
    from packages.music_core.harmony.harmony_engine import build_bar_harmony

    lo = _applied("lo_fi_hiphop")
    game = _applied("game_battle")
    lo_bass = [round(n.start_beat, 2) for n in BassEngine().generate(lo, build_bar_harmony(lo))]
    game_bass = [round(n.start_beat, 2) for n in BassEngine().generate(game, build_bar_harmony(game))]
    assert lo_bass != game_bass
    assert len(game_bass) > len(lo_bass)


def test_generate_api_returns_different_specs_for_templates():
    r1 = client.post("/api/v1/songs/generate", json={"prompt": "一首测试", "style_template_id": "lo_fi_hiphop"})
    r2 = client.post("/api/v1/songs/generate", json={"prompt": "一首测试", "style_template_id": "game_battle"})
    assert r1.status_code == 200 and r2.status_code == 200
    s1, s2 = r1.json()["music_spec"], r2.json()["music_spec"]
    assert s1["seed"] != s2["seed"]
    assert s1["harmony"] != s2["harmony"]
    tracks1 = {t["role"]: t for t in s1["tracks"]}
    tracks2 = {t["role"]: t for t in s2["tracks"]}
    assert tracks1["drums"]["pattern"] == "lofi_swing"
    assert tracks2["drums"]["pattern"] == "battle_drive"


def test_generate_api_without_template_still_works():
    resp = client.post("/api/v1/songs/generate", json={"prompt": "一首测试"})
    assert resp.status_code == 200
    assert resp.json()["song_id"]
