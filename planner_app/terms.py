from __future__ import annotations

from datetime import date, timedelta


HARDCODED_TERMS = {
    "2026": {
        "Term 1": {"start": "2026-02-02", "end": "2026-04-02"},
        "Term 2": {"start": "2026-04-20", "end": "2026-07-03"},
        "Term 3": {"start": "2026-07-20", "end": "2026-09-25"},
        "Term 4": {"start": "2026-10-12", "end": "2026-12-17"},
    },
    "2027": {
        "Term 1": {"start": "2027-02-01", "end": "2027-04-09"},
        "Term 2": {"start": "2027-04-26", "end": "2027-07-02"},
        "Term 3": {"start": "2027-07-19", "end": "2027-09-24"},
        "Term 4": {"start": "2027-10-11", "end": "2027-12-16"},
    },
    "2028": {
        "Term 1": {"start": "2028-02-02", "end": "2028-04-07"},
        "Term 2": {"start": "2028-04-24", "end": "2028-06-30"},
        "Term 3": {"start": "2028-07-17", "end": "2028-09-22"},
        "Term 4": {"start": "2028-10-09", "end": "2028-12-14"},
    },
    "2029": {
        "Term 1": {"start": "2029-01-31", "end": "2029-03-29"},
        "Term 2": {"start": "2029-04-16", "end": "2029-06-29"},
        "Term 3": {"start": "2029-07-16", "end": "2029-09-21"},
        "Term 4": {"start": "2029-10-08", "end": "2029-12-19"},
    },
    "2030": {
        "Term 1": {"start": "2030-02-04", "end": "2030-04-12"},
        "Term 2": {"start": "2030-04-29", "end": "2030-07-05"},
        "Term 3": {"start": "2030-07-22", "end": "2030-09-27"},
        "Term 4": {"start": "2030-10-14", "end": "2030-12-19"},
    },
    "2031": {
        "Term 1": {"start": "2031-02-03", "end": "2031-04-10"},
        "Term 2": {"start": "2031-04-28", "end": "2031-07-04"},
        "Term 3": {"start": "2031-07-21", "end": "2031-09-26"},
        "Term 4": {"start": "2031-10-13", "end": "2031-12-17"},
    },
}


WA_KINGS_BIRTHDAY = {
    2026: date(2026, 9, 28),
    2027: date(2027, 9, 27),
    2028: date(2028, 9, 25),
    2029: date(2029, 9, 24),
    2030: date(2030, 9, 30),
    2031: date(2031, 9, 29),
}


DEFAULT_TERM_NAMES = ["Term 1", "Term 2", "Term 3", "Term 4"]
MAX_TERMS = 6


def parse_iso_date(text: str) -> date:
    year, month, day = map(int, text.split("-"))
    return date(year, month, day)


def _safe_parse(text) -> date | None:
    try:
        return parse_iso_date(str(text))
    except (TypeError, ValueError):
        return None


def get_terms_for_year(year: int, custom_terms: dict | None = None) -> dict:
    """The teacher's own dates for this year if they've set any, else the WA defaults."""
    if custom_terms:
        year_terms = custom_terms.get(str(year), {})
        if year_terms:
            return year_terms
    return HARDCODED_TERMS.get(str(year), {})


def get_term_ranges(year_terms: dict) -> list[tuple[str, date, date]]:
    """(name, start, end) for each term with valid dates, in date order."""
    ranges = []
    for name, term_data in (year_terms or {}).items():
        if not isinstance(term_data, dict):
            continue
        start = _safe_parse(term_data.get("start", ""))
        end = _safe_parse(term_data.get("end", ""))
        if start and end:
            ranges.append((name, start, end))
    ranges.sort(key=lambda item: item[1])
    return ranges


def get_term_names(year: int, custom_terms: dict | None = None) -> list[str]:
    names = [name for name, _start, _end in get_term_ranges(get_terms_for_year(year, custom_terms))]
    return names or list(DEFAULT_TERM_NAMES)


def get_term_week(target_date: date, custom_terms: dict | None = None):
    """Return (year, term name, "Week N") for a date, or (None, None, None) in the holidays."""
    year_terms = get_terms_for_year(target_date.year, custom_terms)
    for name, start, end in get_term_ranges(year_terms):
        if start <= target_date <= end:
            week_num = ((target_date - start).days // 7) + 1
            return str(target_date.year), name, f"Week {week_num}"
    return None, None, None


def is_in_term(target_date: date, custom_terms: dict | None = None) -> bool:
    return get_term_week(target_date, custom_terms)[0] is not None


def validate_terms(year: int, year_terms: dict) -> str | None:
    """Return an error message for a bad set of term dates, or None if it's fine."""
    if not year_terms:
        return "Add at least one term."
    if len(year_terms) > MAX_TERMS:
        return f"A year can have at most {MAX_TERMS} terms."

    for name, term_data in year_terms.items():
        start = _safe_parse(term_data.get("start", ""))
        end = _safe_parse(term_data.get("end", ""))
        if start is None or end is None:
            return f"{name} needs a start and end date."
        if end < start:
            return f"{name} must end after it starts."
        if start.year != int(year) or end.year != int(year):
            return f"{name} must start and end in {year}."

    ranges = get_term_ranges(year_terms)
    for (name_a, _start_a, end_a), (name_b, start_b, _end_b) in zip(ranges, ranges[1:]):
        if start_b <= end_a:
            return f"{name_a} and {name_b} overlap."

    return None


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    d += timedelta(weeks=n - 1)
    return d


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)

    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _apply_weekend_observed(d: date) -> date:
    if d.weekday() == 5:  # Saturday
        return d + timedelta(days=2)
    if d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d


def _easter_sunday(year: int) -> date:
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def get_wa_public_holidays(year: int) -> dict[date, str]:
    holidays: dict[date, str] = {}

    new_year = _apply_weekend_observed(date(year, 1, 1))
    holidays[new_year] = "Public Holiday"

    australia_day = _apply_weekend_observed(date(year, 1, 26))
    holidays[australia_day] = "Public Holiday"

    labour_day = _nth_weekday_of_month(year, 3, 0, 1)  # first Monday in March
    holidays[labour_day] = "Public Holiday"

    easter_sunday = _easter_sunday(year)
    good_friday = easter_sunday - timedelta(days=2)
    easter_monday = easter_sunday + timedelta(days=1)

    holidays[good_friday] = "Public Holiday"
    holidays[easter_sunday] = "Public Holiday"
    holidays[easter_monday] = "Public Holiday"

    anzac_day = date(year, 4, 25)
    holidays[anzac_day] = "Public Holiday"

    wa_day = _nth_weekday_of_month(year, 6, 0, 1)  # first Monday in June
    holidays[wa_day] = "Public Holiday"

    kings_birthday = WA_KINGS_BIRTHDAY.get(year)
    if kings_birthday:
        holidays[kings_birthday] = "Public Holiday"

    christmas = date(year, 12, 25)
    boxing_day = date(year, 12, 26)

    christmas_obs = _apply_weekend_observed(christmas)
    boxing_obs = _apply_weekend_observed(boxing_day)

    if boxing_obs == christmas_obs:
        boxing_obs = boxing_obs + timedelta(days=1)

    holidays[christmas_obs] = "Public Holiday"
    holidays[boxing_obs] = "Public Holiday"

    return holidays


def get_day_block_label(
    target_date: date,
    custom_terms: dict | None = None,
    show_public_holidays: bool = True,
) -> str | None:
    in_term = is_in_term(target_date, custom_terms)
    is_public_holiday = show_public_holidays and target_date in get_wa_public_holidays(target_date.year)

    if not in_term and is_public_holiday:
        return "School Holidays\nPublic Holiday"
    if not in_term:
        return "School Holidays"
    if is_public_holiday:
        return "Public Holiday"
    return None