from __future__ import annotations

from datetime import date, datetime, time
from typing import Dict, Any, List, Optional

from planner_app.timetable import DAYS


DATE_FMT = "%Y-%m-%d"


def iso_monday_for_day(some_date: date) -> str:
    monday = some_date.fromordinal(some_date.toordinal() - some_date.weekday())
    return monday.isoformat()


def get_week_key(view_date: date) -> str:
    return iso_monday_for_day(view_date)


def _ensure_class_record(data: Dict[str, Any], week_key: str, day_name: str, period: int, class_name: str) -> Dict[str, Any]:
    weekly = data.setdefault("weekly_classes", {})
    week_bucket = weekly.setdefault(week_key, {})
    key = f"{day_name}_P{period}"
    if key not in week_bucket:
        week_bucket[key] = {
            "class_name": class_name,
            "topic": "",
            "printed_resources": False,
            "notes": "",
            "homework": "",
            "priority": "",
            "assignment_name": "",
            "assignment_due_date": "",
        }
    return week_bucket[key]


def get_class_details(data: Dict[str, Any], week_key: str, day_name: str, period: int, class_name: str) -> Dict[str, Any]:
    return _ensure_class_record(data, week_key, day_name, period, class_name)


def save_class_details(
    data: Dict[str, Any],
    week_key: str,
    day_name: str,
    period: int,
    class_name: str,
    details: Dict[str, Any],
) -> None:
    record = _ensure_class_record(data, week_key, day_name, period, class_name)
    record.update(details)
    record["class_name"] = class_name


def _class_lessons(data: Dict[str, Any]) -> List[tuple[str, Dict[str, Any]]]:
    timetable = data.get("timetable", {})
    return [
        (day_name, entry)
        for day_name in DAYS
        for entry in timetable.get(day_name, [])
        if entry.get("type") == "class" and str(entry.get("label", "")).strip()
    ]


def ensure_week_records(data: Dict[str, Any], week_key: str) -> None:
    # Each week gets its own records, so "printed resources" starts unticked
    # for a new week without clearing ticks already made this week.
    for day_name, entry in _class_lessons(data):
        _ensure_class_record(data, week_key, day_name, entry["period"], entry["label"])


def get_missing_topics_for_week(data: Dict[str, Any], week_key: str) -> List[Dict[str, Any]]:
    missing: List[Dict[str, Any]] = []
    for day_name, entry in _class_lessons(data):
        details = get_class_details(data, week_key, day_name, entry["period"], entry["label"])
        if not details.get("topic", "").strip():
            missing.append(
                {
                    "day": day_name,
                    "period": entry["period"],
                    "class_name": entry["label"],
                }
            )
    return missing


def should_show_friday_prompt(now: datetime, app_state: Dict[str, Any], day_end: time = time(14, 50)) -> bool:
    # day_end is when the teacher's last period finishes (see timetable.get_day_end_time).
    last = app_state.get("last_topic_prompt_date", "")
    return now.weekday() == 4 and now.time() >= day_end and last != now.date().isoformat()


def should_show_monday_prompt(now: datetime, week_key: str, data: Dict[str, Any]) -> bool:
    if now.weekday() != 0:
        return False
    if now.time() < time(7, 0):
        return False
    app_state = data.get("app_state", {})
    if app_state.get("last_monday_prompt_date", "") == now.date().isoformat():
        return False
    return len(get_missing_topics_for_week(data, week_key)) > 0
