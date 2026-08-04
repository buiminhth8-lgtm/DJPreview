"""风格模板库测试。"""

import pytest

from packages.music_core.instruments.registry import is_known_instrument
from packages.music_core.styles.style_library import find_style_templates, get_style_template, list_style_templates


def test_list_returns_at_least_8():
    assert len(list_style_templates()) >= 8


def test_get_cinematic_piano():
    template = get_style_template("cinematic_piano")
    assert template.id == "cinematic_piano"
    assert "piano" in template.tags


def test_missing_template_raises():
    with pytest.raises(ValueError):
        get_style_template("not_a_template")


def test_find_by_query_and_tag():
    assert find_style_templates(query="chinese")
    assert find_style_templates(tags=["rock"])


def test_all_templates_valid_pydantic():
    for template in list_style_templates():
        assert template.id and template.name
        assert template.default_length_bars >= 8


def test_all_template_instruments_resolvable():
    """T17：所有内置风格模板的乐器都能被 registry 识别。"""
    for template in list_style_templates():
        assert template.default_tracks, template.id
        for tpl in template.default_tracks:
            instrument = tpl.get("instrument")
            assert instrument, (template.id, tpl)
            assert is_known_instrument(instrument), (template.id, instrument)
