from datetime import date

import pytest

from planner_app import settings


def test_preset_theme_is_a_copy():
    theme = settings.get_theme({"current_theme": "Forest"})
    assert theme == settings.PRESET_THEMES["Forest"]
    theme["bg"] = "#000000"
    assert settings.PRESET_THEMES["Forest"]["bg"] != "#000000"


def test_unknown_or_missing_theme_falls_back_to_apricot():
    assert settings.get_theme({}) == settings.PRESET_THEMES["Apricot"]
    assert settings.get_theme({"current_theme": "Nope"}) == settings.PRESET_THEMES["Apricot"]


def test_custom_theme_overrides_only_filled_values():
    theme = settings.get_theme(
        {"current_theme": "Custom", "custom_theme": {"bg": "#111111", "accent": ""}}
    )
    assert theme["bg"] == "#111111"
    assert theme["accent"] == settings.PRESET_THEMES["Apricot"]["accent"]


def test_pd_day_helpers():
    data = {}
    settings.add_pd_day(data, "2026-11-02")
    settings.add_pd_day(data, "2026-10-05")
    settings.add_pd_day(data, "2026-11-02")
    assert data["pd_days"] == ["2026-10-05", "2026-11-02"]
    assert settings.is_pd_day(data, date(2026, 11, 2))

    settings.remove_pd_day(data, "2026-11-02")
    assert not settings.is_pd_day(data, date(2026, 11, 2))

    with pytest.raises(ValueError):
        settings.add_pd_day(data, "02/11/2026")
