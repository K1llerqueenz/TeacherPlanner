from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from planner_app.terms import HARDCODED_TERMS


DATE_FMT = "%Y-%m-%d"
REMINDER_DAYS_BEFORE = 14

DAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
}


def parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value

    if value is None:
        return None

    try:
        return datetime.strptime(str(value), DATE_FMT).date()
    except (TypeError, ValueError):
        return None


def format_display_date(value: date) -> str:
    return f"{value.day} {value.strftime('%b %y')}"


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _extract_number(value: Any) -> Optional[int]:
    text = _safe_str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None

def _build_reminder_item(
    title: str,
    item_date: date,
    source: str,
    class_name: str = "",
) -> Dict[str, Any]:
    clean_title = title.strip()
    clean_class = class_name.strip()

    if clean_class:
        display_text = f"{clean_class}\n{format_display_date(item_date)}\n{clean_title}"
    else:
        display_text = f"{format_display_date(item_date)}\n{clean_title}"

    return {
        "title": clean_title,
        "date": item_date.isoformat(),
        "source": source,
        "class_name": clean_class,
        "display_text": display_text,
    }

def _normalise_class_name(value: Any) -> str:
    return _safe_str(value).lower()


def _get_term_start_date(data: Dict[str, Any], year_value: Any, term_value: Any) -> Optional[date]:
    settings = data.get("settings", {})
    terms = settings.get("terms", {})

    year_str = str(year_value).strip()
    term_str = str(term_value).strip()

    if not year_str or not term_str:
        return None

    # First try saved user settings
    year_terms = terms.get(year_str)
    if year_terms is None:
        try:
            year_terms = terms.get(int(year_str))
        except (TypeError, ValueError):
            year_terms = None

    # Fall back to the WA defaults, same as terms.get_terms_for_year
    if not isinstance(year_terms, dict) or not year_terms:
        year_terms = HARDCODED_TERMS.get(year_str, {})

    if not isinstance(year_terms, dict):
        return None

    term_info = year_terms.get(term_str)
    if not isinstance(term_info, dict):
        return None

    for key in ("start", "start_date", "term_start", "from"):
        parsed = parse_date(term_info.get(key))
        if parsed is not None:
            return parsed

    return None

def _build_class_lesson_map(data: Dict[str, Any], class_name: str) -> Dict[int, int]:
    timetable = data.get("timetable", {})
    if not isinstance(timetable, dict):
        return {}

    class_name = _normalise_class_name(class_name)
    lesson_counter = 0
    lesson_map: Dict[int, int] = {}

    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        day_entries = timetable.get(day, [])
        if not isinstance(day_entries, list):
            continue

        for entry in day_entries:
            if not isinstance(entry, dict):
                continue

            if str(entry.get("type", "")).strip().lower() != "class":
                continue

            entry_class = _normalise_class_name(entry.get("label"))
            if entry_class == class_name:
                lesson_counter += 1
                lesson_map[lesson_counter] = DAY_INDEX[day.lower()]

    return lesson_map


def _assignment_to_date(item: Dict[str, Any], data: Dict[str, Any]) -> Optional[date]:
    year_value = item.get("year")
    term_value = item.get("term")
    week_value = item.get("week")
    lesson_value = item.get("lesson")
    class_value = (
        item.get("class")
        or item.get("class_name")
        or item.get("subject")
        or item.get("label")
    )

    term_start = _get_term_start_date(data, year_value, term_value)
    if term_start is None:
        return None

    week_number = _extract_number(week_value)
    lesson_number = _extract_number(lesson_value)
    class_name = _normalise_class_name(class_value)

    if week_number is None or lesson_number is None or not class_name:
        return None

    lesson_map = _build_class_lesson_map(data, class_name)
    weekday_index = lesson_map.get(lesson_number)

    if weekday_index is None:
        return None

    resolved = term_start + timedelta(weeks=week_number - 1, days=weekday_index)

    return resolved


def _extract_assignment_reminders(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    reminders: List[Dict[str, Any]] = []

    for item in data.get("assignments", []):
        if not isinstance(item, dict):
            continue

        title = _safe_str(item.get("title") or item.get("name"))
        if not title:
            continue

        raw_date = item.get("date") or item.get("due_date")
        item_date = parse_date(raw_date)

        if item_date is None:
            item_date = _assignment_to_date(item, data)

        if item_date is None:
            continue

        class_name = _safe_str(
            item.get("class")
            or item.get("class_name")
            or item.get("subject")
            or item.get("label")
        )

        reminders.append(
            _build_reminder_item(title, item_date, "assignment", class_name=class_name)
        )

    return reminders


def _extract_pd_day_reminders(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    reminders: List[Dict[str, Any]] = []

    for item in data.get("pd_days", []):
        if not isinstance(item, dict):
            continue

        title = _safe_str(item.get("title") or item.get("name") or item.get("label") or "PD Day")
        raw_date = item.get("date")

        item_date = parse_date(raw_date)
        if item_date is None:
            continue

        reminders.append(_build_reminder_item(title, item_date, "pd_day", class_name="PD Day"))

    return reminders


# ============================================================
# FUTURE LEARNING SUPPORT TASK REMINDERS
# Add your learning support task reminder extraction function here.
# ============================================================


def get_all_reminder_items(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    items.extend(_extract_assignment_reminders(data))
    items.extend(_extract_pd_day_reminders(data))

    seen: set[Tuple[str, str, str]] = set()
    unique_items: List[Dict[str, Any]] = []

    for item in items:
        key = (item["source"], item["title"].strip().lower(), item["date"])
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    unique_items.sort(key=lambda item: (item["date"], item["title"].lower()))
    return unique_items


def is_reminder_active(item_date: date, today: date, days_before: int = REMINDER_DAYS_BEFORE) -> bool:
    start_date = item_date - timedelta(days=days_before)
    return start_date <= today <= item_date


def get_active_reminders(data: Dict[str, Any], today: Optional[date] = None) -> List[Dict[str, Any]]:
    today = today or date.today()
    active: List[Dict[str, Any]] = []

    for item in get_all_reminder_items(data):
        item_date = parse_date(item["date"])
        if item_date is None:
            continue

        if is_reminder_active(item_date, today):
            enriched = dict(item)
            enriched["days_left"] = (item_date - today).days
            active.append(enriched)

    active.sort(key=lambda item: (item["date"], item["title"].lower()))
    return active


def get_reminder_display_lines(data: Dict[str, Any], today: Optional[date] = None) -> List[str]:
    active = get_active_reminders(data, today=today)

    if not active:
        return ["No upcoming reminders"]

    return [item["display_text"] for item in active]