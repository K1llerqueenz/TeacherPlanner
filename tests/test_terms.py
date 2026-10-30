from datetime import date

from planner_app import terms


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
