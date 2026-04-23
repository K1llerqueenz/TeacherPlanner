from __future__ import annotations

import platform
from ctypes import wintypes
import ctypes
from pathlib import Path
from typing import List

from planner_app.storage import FONTS_DIR


PRESET_THEMES = {
    "Apricot": {
        "bg": "#f2dfe3",
        "panel": "#f2dfe3",
        "accent": "#ef8db4",
        "text": "#2b2425",
        "outline": "#efb7c7",
        "Monday Border": "#f3a4a7",
        "Tuesday Border": "#f1cb93",
        "Wednesday Border": "#d6a6ef",
        "Thursday Border": "#a8dea1",
        "Friday Border": "#8fdfe8",
        "todo_bg": "#eef1a5",
        "reminder_bg": "#f0cea9",
        "class_fill": "#f3d3e3",
    },
    "Forest": {
        "bg": "#eef5ef",
        "panel": "#f8fbf8",
        "accent": "#6eab79",
        "text": "#203122",
        "outline": "#b6d7be",
        "Monday Border": "#93c49a",
        "Tuesday Border": "#a8d1aa",
        "Wednesday Border": "#bfdcb2",
        "Thursday Border": "#84ba92",
        "Friday Border": "#9ad0bf",
        "todo_bg": "#dbeeb7",
        "reminder_bg": "#d9c9a8",
        "class_fill": "#f3d3e3",
    },
    "Lavender": {
        "bg": "#f4eef8",
        "panel": "#f9f8fb",
        "accent": "#b887dd",
        "text": "#2e2437",
        "outline": "#dcc7f0",
        "Monday Border": "#e8b7ce",
        "Tuesday Border": "#eed0aa",
        "Wednesday Border": "#cfabea",
        "Thursday Border": "#b9ddb5",
        "Friday Border": "#a9dcea",
        "todo_bg": "#ebf0b1",
        "reminder_bg": "#f0ceb1",
        "class_fill": "#f3d3e3",
    }
}


def get_theme(settings: dict) -> dict:
    current_theme = settings.get("current_theme", "Apricot")

    if current_theme == "Custom":
        base_theme = PRESET_THEMES["Apricot"].copy()
        custom = settings.get("custom_theme", {})

        for key, value in custom.items():
            if value:
                base_theme[key] = value

        return base_theme

    return PRESET_THEMES.get(current_theme, PRESET_THEMES["Apricot"]).copy()


def load_local_fonts() -> List[str]:
    loaded: List[str] = []
    font_files = list(Path(FONTS_DIR).glob("*.ttf")) + list(Path(FONTS_DIR).glob("*.otf"))
    if platform.system() == "Windows":
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        fr_private = 0x10
        add_font = gdi32.AddFontResourceExW
        add_font.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID]
        add_font.restype = wintypes.INT
        for font_file in font_files:
            result = add_font(str(font_file), fr_private, 0)
            if result > 0:
                loaded.append(font_file.stem)
    return loaded


def font_folder_path() -> str:
    return str(FONTS_DIR)

from datetime import date, datetime

def normalise_date_string(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").date().isoformat()


def get_pd_days(data: dict) -> set[str]:
    return set(data.get("pd_days", []))


def is_pd_day(data: dict, check_date: date) -> bool:
    return check_date.isoformat() in get_pd_days(data)


def add_pd_day(data: dict, day_str: str) -> None:
    day_str = normalise_date_string(day_str)
    pd_days = set(data.get("pd_days", []))
    pd_days.add(day_str)
    data["pd_days"] = sorted(pd_days)


def remove_pd_day(data: dict, day_str: str) -> None:
    day_str = normalise_date_string(day_str)
    pd_days = set(data.get("pd_days", []))
    pd_days.discard(day_str)
    data["pd_days"] = sorted(pd_days)
