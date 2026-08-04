"""T17：统一乐器注册表测试。"""

from packages.music_core.instruments.registry import (
    get_gm_program,
    is_drum_instrument,
    is_known_instrument,
    list_instruments,
    normalize_instrument_name,
    resolve_instrument,
)


def test_alias_normalize():
    assert normalize_instrument_name("piano") == "acoustic_grand_piano"
    assert normalize_instrument_name("strings") == "string_ensemble_1"
    assert normalize_instrument_name("bass") == "electric_bass_finger"
    assert normalize_instrument_name("drums") == "standard_drum_kit"
    assert normalize_instrument_name("pad") == "pad_2_warm"
    assert normalize_instrument_name("synth_pad") == "pad_2_warm"
    assert normalize_instrument_name("string_ensemble") == "string_ensemble_1"


def test_case_space_hyphen_compatibility():
    assert normalize_instrument_name("Grand Piano") == "acoustic_grand_piano"
    assert normalize_instrument_name("electric-guitar") == "electric_guitar_clean"
    assert normalize_instrument_name("  SYNTH-PAD  ") == "pad_2_warm"


def test_gm_program():
    assert get_gm_program("piano") == 0
    assert get_gm_program("acoustic_grand_piano") == 0
    assert get_gm_program("bass") == 33
    assert get_gm_program("strings") == 48
    assert get_gm_program("electric_guitar_clean") == 27
    assert get_gm_program("erhu") == 110


def test_drum_instrument():
    assert is_drum_instrument("drums") is True
    assert is_drum_instrument("standard_drum_kit") is True
    assert is_drum_instrument("drum_kit") is True
    assert is_drum_instrument("piano") is False


def test_unknown_instrument():
    assert is_known_instrument("unknown_xyz") is False
    assert normalize_instrument_name("unknown_xyz") == "unknown_xyz"
    assert get_gm_program("unknown_xyz", default=0) == 0
    info = resolve_instrument("unknown_xyz")
    assert info.gm_program is None
    assert info.family == "unknown"


def test_list_instruments_has_core_and_valid_programs():
    instruments = list_instruments()
    ids = {item.id for item in instruments}
    assert "acoustic_grand_piano" in ids
    assert "standard_drum_kit" in ids
    assert "string_ensemble_1" in ids
    assert "electric_bass_finger" in ids
    assert all(item.gm_program is None or 0 <= item.gm_program <= 127 for item in instruments)


def test_drum_canonical_has_no_melodic_program():
    assert resolve_instrument("drums").gm_program is None
    assert resolve_instrument("standard_drum_kit").is_drum is True
