from planner_app import storage
from planner_app.settings import BUNDLED_FONTS


def test_bundled_fonts_match_folder_and_have_licences():
    on_disk = {p.name for p in storage.FONTS_DIR.iterdir() if p.suffix in {".ttf", ".otf"}}
    assert on_disk == set(BUNDLED_FONTS)

    licences = [p.name for p in (storage.FONTS_DIR / "licenses").iterdir()]
    for font_file in BUNDLED_FONTS:
        prefix = font_file.split("-")[0]
        assert any(name.startswith(prefix + "-") for name in licences), font_file


def test_legacy_fonts_map_to_bundled_ones():
    assert set(storage.LEGACY_FONT_REPLACEMENTS.values()) <= set(BUNDLED_FONTS.values())


def test_saved_demo_fonts_are_replaced_on_load(data_dir):
    data = storage.load_data()
    data["settings"]["font_family"] = "Restweek"
    data["settings"]["font_sections"] = {"term_title": "Jraot-Regular", "popup_text": "Arial"}
    storage.save_data(data)

    settings = storage.load_data()["settings"]

    assert settings["font_family"] == "Allison"
    assert settings["font_sections"] == {"term_title": "Bungee", "popup_text": "Arial"}
