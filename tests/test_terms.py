from datetime import date

from planner_app import terms


def test_easter_sunday_known_years():
    assert terms._easter_sunday(2026) == date(2026, 4, 5)
    assert terms._easter_sunday(2027) == date(2027, 3, 28)
    assert terms._easter_sunday(2030) == date(2030, 4, 21)


def test_weekend_holidays_move_to_monday():
    assert terms._apply_weekend_observed(date(2028, 1, 1)) == date(2028, 1, 3)  # Saturday
    assert terms._apply_weekend_observed(date(2034, 1, 1)) == date(2034, 1, 2)  # Sunday
    assert terms._apply_weekend_observed(date(2026, 1, 1)) == date(2026, 1, 1)  # Thursday


def test_wa_public_holidays_2026():
    holidays = terms.get_wa_public_holidays(2026)
    expected = {
        date(2026, 1, 1),   # New Year's Day
        date(2026, 1, 26),  # Australia Day
        date(2026, 3, 2),   # Labour Day
        date(2026, 4, 3),   # Good Friday
        date(2026, 4, 5),   # Easter Sunday
        date(2026, 4, 6),   # Easter Monday
        date(2026, 4, 25),  # Anzac Day
        date(2026, 6, 1),   # WA Day
        date(2026, 9, 28),  # King's Birthday
        date(2026, 12, 25),
        date(2026, 12, 28),  # Boxing Day falls on a Saturday
    }
    assert set(holidays) == expected


def test_christmas_and_boxing_day_never_share_a_date():
    # Christmas 2027 is a Saturday, so both move into the following week.
    holidays = terms.get_wa_public_holidays(2027)
    assert date(2027, 12, 27) in holidays
    assert date(2027, 12, 28) in holidays


def test_is_in_term_uses_hardcoded_dates():
    assert terms.is_in_term(date(2026, 2, 2))
    assert terms.is_in_term(date(2026, 12, 17))
    assert not terms.is_in_term(date(2026, 4, 10))
    assert not terms.is_in_term(date(2040, 3, 1))


def test_custom_terms_override_hardcoded():
    custom = {"2026": {"Term 1": {"start": "2026-01-28", "end": "2026-03-27"}}}
    assert terms.is_in_term(date(2026, 1, 28), custom)
    assert not terms.is_in_term(date(2026, 4, 1), custom)


def test_incomplete_custom_terms_are_skipped():
    custom = {"2026": {"Term 1": {"start": "2026-02-02", "end": ""}}}
    assert not terms.is_in_term(date(2026, 2, 10), custom)


def test_day_block_label():
    assert terms.get_day_block_label(date(2026, 3, 3)) is None
    assert terms.get_day_block_label(date(2026, 3, 2)) == "Public Holiday"
    assert terms.get_day_block_label(date(2026, 7, 7)) == "School Holidays"
    assert terms.get_day_block_label(date(2026, 4, 6)) == "School Holidays\nPublic Holiday"


def test_wa_dates_are_the_default():
    assert terms.get_term_week(date(2026, 10, 30)) == ("2026", "Term 4", "Week 3")
    assert not terms.is_in_term(date(2026, 10, 1))


def test_teachers_own_dates_replace_the_defaults():
    custom = {"2026": {
        "Autumn": {"start": "2026-09-02", "end": "2026-12-18"},
        "Spring": {"start": "2026-01-05", "end": "2026-03-27"},
    }}
    assert terms.get_term_names(2026, custom) == ["Spring", "Autumn"]
    assert terms.get_term_week(date(2026, 9, 9), custom) == ("2026", "Autumn", "Week 2")
    # A WA term day is a holiday for this school.
    assert terms.get_day_block_label(date(2026, 4, 30), custom, show_public_holidays=False) == "School Holidays"
    # Years without custom dates still use the defaults.
    assert terms.get_term_week(date(2027, 2, 1), custom)[1] == "Term 1"


def test_public_holidays_can_be_turned_off():
    assert terms.get_day_block_label(date(2026, 6, 1)) == "Public Holiday"  # WA Day
    assert terms.get_day_block_label(date(2026, 6, 1), show_public_holidays=False) is None


def test_year_without_any_dates_falls_back_to_term_names():
    assert terms.get_term_names(2040) == terms.DEFAULT_TERM_NAMES
    assert terms.get_term_week(date(2040, 3, 1)) == (None, None, None)


def test_validate_terms():
    good = {"Term 1": {"start": "2026-02-02", "end": "2026-04-02"},
            "Term 2": {"start": "2026-04-20", "end": "2026-07-03"}}
    assert terms.validate_terms(2026, good) is None
    assert terms.validate_terms(2026, {}) is not None
    assert "needs a start" in terms.validate_terms(2026, {"Term 1": {"start": "", "end": "2026-04-02"}})
    assert "end after" in terms.validate_terms(2026, {"Term 1": {"start": "2026-04-02", "end": "2026-02-02"}})
    assert "in 2026" in terms.validate_terms(2026, {"Term 1": {"start": "2025-12-01", "end": "2026-02-02"}})
    overlap = dict(good, **{"Term 2": {"start": "2026-03-30", "end": "2026-07-03"}})
    assert "overlap" in terms.validate_terms(2026, overlap)
