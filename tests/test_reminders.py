from datetime import date

from planner_app import reminders


def _data(**extra):
    data = {
        "settings": {"terms": {}},
        "timetable": {
            "Monday": [{"period": 1, "label": "9.3", "type": "class"}],
            "Tuesday": [{"period": 2, "label": "DOTT", "type": "label"}],
            "Wednesday": [{"period": 3, "label": "9.3", "type": "class"}],
        },
        "assignments": [],
        "pd_days": [],
    }
    data.update(extra)
    return data


def test_parse_date():
    assert reminders.parse_date("2026-10-30") == date(2026, 10, 30)
    assert reminders.parse_date(date(2026, 1, 1)) == date(2026, 1, 1)
    assert reminders.parse_date("30/10/2026") is None
    assert reminders.parse_date(None) is None


def test_display_date_format():
    assert reminders.format_display_date(date(2026, 3, 5)) == "5 Mar 26"


def test_assignment_with_explicit_date():
    data = _data(assignments=[{"title": " Essay ", "due_date": "2026-11-05", "class": "9.3"}])
    [item] = reminders.get_all_reminder_items(data)
    assert item == {
        "title": "Essay",
        "date": "2026-11-05",
        "source": "assignment",
        "class_name": "9.3",
        "display_text": "9.3\n5 Nov 26\nEssay",
    }


def test_assignment_date_from_term_week_and_lesson():
    # Term 4 2026 starts Monday 12 Oct. Week 3, lesson 2 of 9.3 is the Wednesday.
    data = _data(
        assignments=[
            {"title": "Test", "year": "2026", "term": "Term 4", "week": "Week 3", "lesson": "Lesson 2", "class": "9.3"}
        ]
    )
    [item] = reminders.get_all_reminder_items(data)
    assert item["date"] == "2026-10-28"


def test_assignment_uses_custom_term_start():
    data = _data(
        assignments=[{"title": "Quiz", "year": 2026, "term": "Term 1", "week": 1, "lesson": 1, "class": "9.3"}]
    )
    data["settings"]["terms"] = {"2026": {"Term 1": {"start": "2026-01-26", "end": "2026-04-02"}}}
    [item] = reminders.get_all_reminder_items(data)
    assert item["date"] == "2026-01-26"


def test_unresolvable_assignments_are_skipped():
    data = _data(
        assignments=[
            {"title": "", "due_date": "2026-11-05"},
            {"title": "No date"},
            {"title": "Unknown class", "year": "2026", "term": "Term 4", "week": 1, "lesson": 1, "class": "12.1"},
            {"title": "Too many lessons", "year": "2026", "term": "Term 4", "week": 1, "lesson": 5, "class": "9.3"},
            "not a dict",
        ]
    )
    assert reminders.get_all_reminder_items(data) == []


def test_pd_day_reminders_and_dedupe():
    data = _data(
        pd_days=[
            {"date": "2026-11-02", "type": "full"},
            {"date": "2026-11-02", "type": "full"},
            {"date": "bad"},
        ]
    )
    items = reminders.get_all_reminder_items(data)
    assert len(items) == 1
    assert items[0]["title"] == "PD Day"
    assert items[0]["source"] == "pd_day"


def test_items_sorted_by_date_then_title():
    data = _data(
        assignments=[
            {"title": "b", "date": "2026-11-05"},
            {"title": "A", "date": "2026-11-05"},
            {"title": "c", "date": "2026-11-01"},
        ]
    )
    assert [i["title"] for i in reminders.get_all_reminder_items(data)] == ["c", "A", "b"]


def test_active_window_is_two_weeks():
    due = date(2026, 11, 14)
    assert reminders.is_reminder_active(due, date(2026, 10, 31))
    assert reminders.is_reminder_active(due, due)
    assert not reminders.is_reminder_active(due, date(2026, 10, 30))
    assert not reminders.is_reminder_active(due, date(2026, 11, 15))


def test_active_reminders_and_display_lines():
    data = _data(
        assignments=[
            {"title": "Soon", "date": "2026-11-03"},
            {"title": "Later", "date": "2026-12-25"},
        ]
    )
    today = date(2026, 10, 30)
    [active] = reminders.get_active_reminders(data, today=today)
    assert active["title"] == "Soon"
    assert active["days_left"] == 4
    assert reminders.get_reminder_display_lines(data, today=today) == ["3 Nov 26\nSoon"]
    assert reminders.get_reminder_display_lines(_data(), today=today) == ["No upcoming reminders"]
