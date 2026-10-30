from datetime import datetime

from planner_app import topics


def _data():
    return {
        "weekly_classes": {},
        "timetable": {
            "Monday": [
                {"period": 1, "label": "9.3", "type": "class"},
                {"period": 2, "label": "DOTT", "type": "label"},
                {"period": 3, "label": "", "type": "class"},
            ],
            "Tuesday": [{"period": 4, "label": "7.11", "type": "class"}],
        },
    }


def test_ensure_week_records_keeps_printed_ticks():
    data = _data()
    week = "2026-10-26"
    topics.save_class_details(data, week, "Monday", 1, "9.3", {"printed_resources": True})

    topics.ensure_week_records(data, week)

    assert data["weekly_classes"][week]["Monday_P1"]["printed_resources"] is True


def test_new_week_starts_unticked():
    data = _data()
    topics.save_class_details(data, "2026-10-26", "Monday", 1, "9.3", {"printed_resources": True})

    topics.ensure_week_records(data, "2026-11-02")

    assert data["weekly_classes"]["2026-11-02"]["Monday_P1"]["printed_resources"] is False


def test_missing_topics_use_users_timetable():
    data = _data()
    week = "2026-10-26"
    topics.save_class_details(data, week, "Tuesday", 4, "7.11", {"topic": "Fractions"})

    missing = topics.get_missing_topics_for_week(data, week)

    assert missing == [{"day": "Monday", "period": 1, "class_name": "9.3"}]


def test_monday_prompt_only_when_topics_missing():
    data = _data()
    data["app_state"] = {}
    monday_morning = datetime(2026, 10, 26, 8, 0)
    week = topics.get_week_key(monday_morning.date())

    assert topics.should_show_monday_prompt(monday_morning, week, data)

    for day, period, name in [("Monday", 1, "9.3"), ("Tuesday", 4, "7.11")]:
        topics.save_class_details(data, week, day, period, name, {"topic": "x"})
    assert not topics.should_show_monday_prompt(monday_morning, week, data)


def test_friday_prompt_after_last_period():
    assert topics.should_show_friday_prompt(datetime(2026, 10, 30, 15, 0), {})
    assert not topics.should_show_friday_prompt(datetime(2026, 10, 30, 14, 0), {})
    assert not topics.should_show_friday_prompt(
        datetime(2026, 10, 30, 15, 0), {"last_topic_prompt_date": "2026-10-30"}
    )


def test_friday_prompt_follows_teachers_last_bell():
    from datetime import time

    assert not topics.should_show_friday_prompt(datetime(2026, 10, 30, 15, 0), {}, time(15, 20))
    assert topics.should_show_friday_prompt(datetime(2026, 10, 30, 15, 20), {}, time(15, 20))


def test_week_key_is_monday():
    assert topics.get_week_key(datetime(2026, 10, 30).date()) == "2026-10-26"
    assert topics.get_week_key(datetime(2026, 10, 26).date()) == "2026-10-26"
    assert topics.get_week_key(datetime(2026, 11, 1).date()) == "2026-10-26"


def test_save_class_details_keeps_class_name():
    data = _data()
    topics.save_class_details(data, "2026-10-26", "Monday", 1, "9.3", {"topic": "Algebra", "class_name": "x"})
    record = topics.get_class_details(data, "2026-10-26", "Monday", 1, "9.3")
    assert record["topic"] == "Algebra"
    assert record["class_name"] == "9.3"


def test_monday_prompt_waits_until_7am_and_shows_once():
    data = _data()
    week = "2026-10-26"
    assert not topics.should_show_monday_prompt(datetime(2026, 10, 26, 6, 59), week, data)
    assert not topics.should_show_monday_prompt(datetime(2026, 10, 27, 8, 0), week, data)

    data["app_state"] = {"last_monday_prompt_date": "2026-10-26"}
    assert not topics.should_show_monday_prompt(datetime(2026, 10, 26, 8, 0), week, data)


def test_friday_prompt_only_on_friday():
    assert not topics.should_show_friday_prompt(datetime(2026, 10, 29, 15, 0), {})
