"""T36：LLM 乐器别名归一化测试。"""

from packages.music_core.instruments.registry import (
    canonical_instrument_name,
    get_gm_program,
    is_drum_instrument,
    is_known_instrument,
    normalize_instrument_name,
)


def test_brass_aliases():
    for name in ("brass", "epic_brass", "cinematic_brass", "orchestral_brass", "horns", "brass_ensemble"):
        assert normalize_instrument_name(name) == "brass_section"
        assert is_known_instrument(name) is True


def test_distortion_guitar_aliases():
    for name in (
        "distortion_guitar",
        "distortion guitar",
        "distorted_guitar",
        "electric_guitar_distorted",
        "electric guitar distorted",
        "dist_guitar",
        "heavy_guitar",
        "metal_guitar",
        "power_chord_guitar",
    ):
        assert normalize_instrument_name(name) == "distortion_guitar"
        assert is_known_instrument(name) is True


def test_overdriven_guitar_aliases():
    assert normalize_instrument_name("overdrive guitar") == "overdriven_guitar"
    assert normalize_instrument_name("overdriven_guitar") == "overdriven_guitar"


def test_clean_electric_guitar_aliases():
    for name in ("electric_guitar", "electric guitar", "clean_electric_guitar"):
        assert normalize_instrument_name(name) == "electric_guitar_clean"


def test_strings_aliases():
    for name in ("strings", "string", "string ensemble", "string_ensemble", "orchestral_strings", "string_ostinato"):
        assert normalize_instrument_name(name) == "string_ensemble_1"


def test_heavy_drums_role_drums():
    for name in ("heavy_drums", "rock_drums", "metal_drums", "battle_drums", "cinematic_drums"):
        assert normalize_instrument_name(name, role="drums") == "standard_drum_kit"
        assert is_drum_instrument(name, role="drums") is True


def test_low_tom_percussion():
    assert normalize_instrument_name("low_tom_percussion", role="drums") == "standard_drum_kit"
    assert is_known_instrument("low_tom_percussion") is True


def test_synth_bass_aliases():
    for name in ("synth_bass", "synth bass", "sub_bass", "electronic_bass"):
        assert normalize_instrument_name(name) == "synth_bass_1"
    assert normalize_instrument_name("bass") == "electric_bass_finger"
    assert normalize_instrument_name("pick_bass") == "electric_bass_pick"


def test_piano_pad_synth_aliases():
    assert normalize_instrument_name("piano") == "acoustic_grand_piano"
    assert normalize_instrument_name("grand_piano") == "acoustic_grand_piano"
    assert normalize_instrument_name("cinematic_piano") == "acoustic_grand_piano"
    assert normalize_instrument_name("electric_piano") == "electric_piano_1"
    assert normalize_instrument_name("pad") == "pad_2_warm"
    assert normalize_instrument_name("synth_pad") == "pad_2_warm"
    assert normalize_instrument_name("ambient_pad") == "pad_1_new_age"
    assert normalize_instrument_name("lead_synth") == "lead_1_square"
    assert normalize_instrument_name("synth_lead") == "lead_2_sawtooth"


def test_plural_normalization():
    assert normalize_instrument_name("trumpets") == "trumpet"
    assert normalize_instrument_name("trombones") == "trombone"
    assert normalize_instrument_name("violins") == "violin"
    assert normalize_instrument_name("cellos") == "cello"
    assert normalize_instrument_name("brasses") == "brass_section"


def test_unknown_instrument_passthrough():
    for name in ("magic_space_laser", "unknown_epic_thing"):
        assert normalize_instrument_name(name) == name
        assert is_known_instrument(name) is False


def test_gm_program_brass_and_guitar():
    assert get_gm_program("brass") == 61
    assert get_gm_program("electric_guitar_distorted") == 30
    assert get_gm_program("strings") == 48
    assert get_gm_program("synth_bass") == 38


def test_canonical_instrument_name_alias():
    assert canonical_instrument_name("brass") == "brass_section"
    assert canonical_instrument_name("electric_guitar_distorted") == "distortion_guitar"
