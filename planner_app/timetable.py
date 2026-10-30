from __future__ import annotations

from datetime import time
from typing import Any, Dict, List, Optional


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Bell times used until a teacher sets their own in Settings > School.
DEFAULT_PERIOD_TIMES: List[Dict[str, str]] = [
    {"start": "08:40", "end": "09:44"},
    {"start": "09:44", "end": "10:48"},
    {"start": "11:13", "end": "12:17"},
    {"start": "12:17", "end": "13:21"},
    {"start": "13:46", "end": "14:50"},
]

MIN_PERIODS = 1
MAX_PERIODS = 12


def parse_clock(text: Any) -> Optional[time]:
    """Parse "8:40", "08:40" or "14:50" into a time. Returns None if invalid."""
    parts = str(text or "").strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour, minute)


def format_clock(value: time) -> str:
    return value.strftime("%H:%M")


def validate_period_times(slots: List[Dict[str, Any]]) -> Optional[str]:
    """Return an error message for a bad list of bell times, or None if it's fine."""
    if not (MIN_PERIODS <= len(slots) <= MAX_PERIODS):
        return f"Choose between {MIN_PERIODS} and {MAX_PERIODS} periods."

    previous_end: Optional[time] = None
    for number, slot in enumerate(slots, start=1):
        start = parse_clock(slot.get("start"))
        end = parse_clock(slot.get("end"))
        if start is None or end is None:
            return f"Period {number} needs a start and end time like 08:40."
        if end <= start:
            return f"Period {number} must end after it starts."
        if previous_end is not None and start < previous_end:
            return f"Period {number} starts before period {number - 1} ends."
        previous_end = end

    return None


def normalise_period_times(slots: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {"start": format_clock(parse_clock(s["start"])), "end": format_clock(parse_clock(s["end"]))}
        for s in slots
    ]


def get_period_times(settings: Dict[str, Any]) -> List[Dict[str, str]]:
    saved = settings.get("period_times")
    if isinstance(saved, list) and saved and validate_period_times(saved) is None:
        return normalise_period_times(saved)
    return [dict(slot) for slot in DEFAULT_PERIOD_TIMES]


def get_period_count(settings: Dict[str, Any]) -> int:
    return len(get_period_times(settings))


def format_period_time(settings: Dict[str, Any], period: int) -> str:
    slots = get_period_times(settings)
    if 1 <= period <= len(slots):
        slot = slots[period - 1]
        return f"{slot['start']} to {slot['end']}"
    return ""


def get_day_end_time(settings: Dict[str, Any]) -> time:
    return parse_clock(get_period_times(settings)[-1]["end"])


def get_periods_before_breaks(settings: Dict[str, Any]) -> set[int]:
    """Periods followed by a gap in the bell times (recess, lunch)."""
    slots = get_period_times(settings)
    return {
        number
        for number, (this, following) in enumerate(zip(slots, slots[1:]), start=1)
        if parse_clock(following["start"]) > parse_clock(this["end"])
    }


def make_blank_lesson(period: int) -> Dict[str, Any]:
    return {"period": period, "label": "", "type": "class", "students": 0}


def make_blank_timetable(period_count: int = len(DEFAULT_PERIOD_TIMES)) -> Dict[str, List[Dict[str, Any]]]:
    return {day: [make_blank_lesson(p) for p in range(1, period_count + 1)] for day in DAYS}


def resize_timetable(timetable: Dict[str, List[Dict[str, Any]]], period_count: int) -> None:
    """Add blank periods or drop extra ones so every day has period_count lessons."""
    for day in DAYS:
        lessons = [entry for entry in timetable.get(day, []) if isinstance(entry, dict)]
        by_period = {entry.get("period"): entry for entry in lessons}
        timetable[day] = [
            by_period.get(period) or make_blank_lesson(period)
            for period in range(1, period_count + 1)
        ]
