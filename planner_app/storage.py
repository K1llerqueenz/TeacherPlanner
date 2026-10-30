from __future__ import annotations

import json
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from planner_app.timetable import DAYS


BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"

# Earlier builds bundled demo / personal-use-only fonts. They were swapped for
# freely licensed look-alikes, so map any saved choice onto its replacement.
LEGACY_FONT_REPLACEMENTS = {
    "Jraot": "Bungee",
    "Jraot-Regular": "Bungee",
    "Jraot Outline": "Bungee Outline",
    "Jraot-Outline": "Bungee Outline",
    "Jraot Hollow": "Bungee Shade",
    "Jraot-Hollow": "Bungee Shade",
    "Jraot Extrude": "Bungee Shade",
    "Jraot-Extrude": "Bungee Shade",
    "Restweek": "Allison",
    "This Appeal": "Bebas Neue",
    "This Appeal Free Demo": "Bebas Neue",
    "ThisAppeal-FreeDemo": "Bebas Neue",
    "Rocket": "Permanent Marker",
    "Rocket Brush": "Permanent Marker",
}

# Older versions saved data.json next to the code, which is inside the app
# bundle once packaged (read-only on Windows, wiped on every update).
LEGACY_DATA_FILE = BASE_DIR / "data.json"


def user_data_dir() -> Path:
    override = os.environ.get("TEACHERPLANNER_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / "TeacherPlanner"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "TeacherPlanner"
    root = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(root) / "teacherplanner"


DATA_DIR = user_data_dir()
DATA_FILE = DATA_DIR / "data.json"
BACKUP_FILE = DATA_DIR / "data.json.bak"


def make_blank_timetable() -> Dict[str, list[dict[str, Any]]]:
    return {
        day: [
            {"period": period, "label": "", "type": "class", "students": 0}
            for period in range(1, 6)
        ]
        for day in DAYS
    }

DEFAULT_DATA: Dict[str, Any] = {
    "todos": [],
    "weekly_classes": {},
    "pd_days": [],
    "assignments": [],
    "topic_overview": {},
    "timetable": {},
    "settings": {
        "current_theme": "Apricot",
        "font_family": "Segoe UI",
        "window_width_ratio": 0.92,
        "window_height_ratio": 0.9,
        "class_colours": {},
        "label_colours": {},
        "font_sections": {},
        "custom_theme": {
            "bg": "#f7eef0",
            "panel": "#f5f5f5",
            "accent": "#ef8db4",
            "text": "#2d2528",
            "outline": "#f2b9c8",
            "Monday Border": "#f3a4a7",
            "Tuesday Border": "#f2cf9b",
            "Wednesday Border": "#d9a3f2",
            "Thursday Border": "#a8e0a0",
            "Friday Border": "#9be4ef",
            "todo_bg": "#eef1a5",
            "reminder_bg": "#f3cfab",
            "pd_day_bg": "#E6CBA8",
            "public_holiday_bg": "#D9C2E9",
            "school_holiday_bg": "#BFDCC3",
        },
        "terms": {},
        "pd_day_bg": "#E6CBA8",
        "public_holiday_bg": "#D9C2E9",
        "school_holiday_bg": "#BFDCC3",
    },
    "app_state": {
        "last_topic_prompt_date": "",
        "last_monday_prompt_date": "",
        "last_seen_date": "",
    },
    "setup": {
        "completed": False,
        "skipped": False,
        "selected_year": "",
    }
}


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists():
        return

    if LEGACY_DATA_FILE.exists():
        shutil.copy2(LEGACY_DATA_FILE, DATA_FILE)
        return

    _write_json(DATA_FILE, deepcopy(DEFAULT_DATA))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    # Write to a temp file and swap it in, so a crash mid-save can't leave a
    # half-written data file behind.
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _set_aside_corrupt_file() -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        os.replace(DATA_FILE, DATA_DIR / f"data.corrupt-{stamp}.json")
    except OSError:
        pass


def load_data() -> Dict[str, Any]:
    ensure_storage()

    data = _read_json(DATA_FILE)
    if data is None:
        _set_aside_corrupt_file()
        data = _read_json(BACKUP_FILE)
        if data is None:
            data = deepcopy(DEFAULT_DATA)
        _write_json(DATA_FILE, data)

    merged = merge_defaults(data, DEFAULT_DATA)

    merged.pop("reminders", None)

    settings = merged.get("settings", {})
    settings.pop("notification_windows", None)
    settings.pop("notification_mac", None)
    replace_legacy_fonts(settings)

    timetable = merged.get("timetable")

    if not timetable:
        timetable = make_blank_timetable()
        merged["timetable"] = timetable
    else:
        for day in DAYS:
            timetable.setdefault(day, [])

    return merged


def replace_legacy_fonts(settings: Dict[str, Any]) -> None:
    family = settings.get("font_family")
    if family in LEGACY_FONT_REPLACEMENTS:
        settings["font_family"] = LEGACY_FONT_REPLACEMENTS[family]

    sections = settings.get("font_sections")
    if isinstance(sections, dict):
        for key, value in sections.items():
            if value in LEGACY_FONT_REPLACEMENTS:
                sections[key] = LEGACY_FONT_REPLACEMENTS[value]


def save_data(data: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists() and _read_json(DATA_FILE) is not None:
        shutil.copy2(DATA_FILE, BACKUP_FILE)

    _write_json(DATA_FILE, data)


def merge_defaults(data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


# -----------------------------
# Auth session helpers
# -----------------------------
def _get_auth(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.setdefault("auth", {
        "current_user": None,
        "auto_login": True,
        "last_user_id": None,
    })


def get_current_user(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    auth = _get_auth(data)
    return auth.get("current_user")


def get_last_user_id(data: Dict[str, Any]) -> Optional[str]:
    auth = _get_auth(data)
    return auth.get("last_user_id")


def set_current_user(data: Dict[str, Any], user: Dict[str, Any], auto_login: bool = True) -> None:
    auth = _get_auth(data)
    auth["current_user"] = {
        "id": user.get("id", ""),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
    }
    auth["auto_login"] = auto_login
    auth["last_user_id"] = user.get("id", "")


def logout_current_user(data: Dict[str, Any]) -> None:
    auth = _get_auth(data)
    auth["current_user"] = None
    auth["auto_login"] = False


def has_users(data: Dict[str, Any]) -> bool:
    # Server now owns the users list, so this just controls UI flow.
    return True


def reset_planner_data(data: Dict[str, Any], keep_settings: bool = True) -> None:
    """
    Reset planner content for a fresh user session.
    Keeps theme/font settings by default so the app still looks the same.
    """
    settings = deepcopy(data.get("settings", DEFAULT_DATA["settings"])) if keep_settings else deepcopy(DEFAULT_DATA["settings"])
    auth = deepcopy(_get_auth(data))

    data.clear()
    data.update(deepcopy(DEFAULT_DATA))
    data["settings"] = settings
    data["auth"] = auth
    data["timetable"] = make_blank_timetable()


def prepare_new_account_local_state(data: Dict[str, Any]) -> None:
    """
    Called after successful account creation.
    Brand new account should always start with clean planner data.
    """
    current_user = deepcopy(get_current_user(data))
    auto_login = _get_auth(data).get("auto_login", True)

    reset_planner_data(data, keep_settings=True)

    if current_user:
        set_current_user(data, current_user, auto_login=auto_login)

    data["setup"]["completed"] = False
    data["setup"]["skipped"] = False
    data["setup"]["selected_year"] = ""
    data["app_state"]["last_topic_prompt_date"] = ""
    data["app_state"]["last_monday_prompt_date"] = ""
    data["app_state"]["last_seen_date"] = ""


def user_changed_on_this_device(data: Dict[str, Any], user: Dict[str, Any]) -> bool:
    last_user_id = get_last_user_id(data)
    new_user_id = user.get("id", "")
    return bool(last_user_id and new_user_id and last_user_id != new_user_id)


def update_current_user_password(
    data: Dict[str, Any],
    current_password: str,
    new_password: str,
) -> tuple[bool, str]:
    from planner_app.auth_api import change_password

    user = get_current_user(data)
    if not user:
        return False, "No signed-in user was found."

    return change_password(user["id"], current_password, new_password)

