from datetime import time

from planner_app import timetable


def test_defaults_match_original_bell_times():
    slots = timetable.get_period_times({})
    assert len(slots) == 5
    assert slots[0] == {"start": "08:40", "end": "09:44"}
    assert timetable.get_day_end_time({}) == time(14, 50)
    assert timetable.get_periods_before_breaks({}) == {2, 4}


def test_saved_bell_times_are_used_and_tidied():
    settings = {"period_times": [
        {"start": "8:30", "end": "9:20"},
        {"start": "9:20", "end": "10:10"},
        {"start": "10:30", "end": "11:20"},
        {"start": "11:20", "end": "12:10"},
        {"start": "12:50", "end": "13:40"},
        {"start": "13:40", "end": "15:10"},
    ]}
    assert timetable.get_period_count(settings) == 6
    assert timetable.get_period_times(settings)[0] == {"start": "08:30", "end": "09:20"}
    assert timetable.get_day_end_time(settings) == time(15, 10)
    assert timetable.format_period_time(settings, 6) == "13:40 to 15:10"
    assert timetable.get_periods_before_breaks(settings) == {2, 4}


def test_broken_saved_bell_times_fall_back_to_defaults():
    settings = {"period_times": [{"start": "nope", "end": "09:00"}]}
    assert timetable.get_period_times(settings) == timetable.DEFAULT_PERIOD_TIMES


def test_validate_period_times():
    ok = [{"start": "08:00", "end": "09:00"}, {"start": "09:00", "end": "10:00"}]
    assert timetable.validate_period_times(ok) is None
    assert "end after" in timetable.validate_period_times([{"start": "09:00", "end": "08:00"}])
    assert "before period 1 ends" in timetable.validate_period_times(
        [{"start": "08:00", "end": "09:00"}, {"start": "08:30", "end": "10:00"}]
    )
    assert timetable.validate_period_times([{"start": "24:00", "end": "25:00"}]) is not None
    assert timetable.validate_period_times([]) is not None
    assert timetable.validate_period_times([dict(start="08:00", end="08:01")] * 13) is not None


def test_resize_timetable_adds_and_drops_periods():
    table = timetable.make_blank_timetable(5)
    table["Monday"][0]["label"] = "9.3"

    timetable.resize_timetable(table, 7)
    assert [e["period"] for e in table["Monday"]] == [1, 2, 3, 4, 5, 6, 7]
    assert table["Monday"][0]["label"] == "9.3"
    assert table["Friday"][6] == timetable.make_blank_lesson(7)

    timetable.resize_timetable(table, 3)
    assert [e["period"] for e in table["Tuesday"]] == [1, 2, 3]
    assert table["Monday"][0]["label"] == "9.3"
