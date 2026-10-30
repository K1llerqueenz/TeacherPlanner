import json

from planner_app import storage


def test_user_data_dir_honours_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TEACHERPLANNER_DATA_DIR", str(tmp_path))
    assert storage.user_data_dir() == tmp_path


def test_first_run_creates_default_file(data_dir):
    data = storage.load_data()
    assert (data_dir / "data.json").exists()
    assert data["todos"] == []
    assert set(data["timetable"]) == {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}


def test_migrates_legacy_file(data_dir):
    legacy = data_dir / "legacy" / "data.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps({"todos": [{"text": "old", "completed": False}]}))

    data = storage.load_data()

    assert data["todos"] == [{"text": "old", "completed": False}]
    assert legacy.exists()


def test_save_round_trip_and_backup(data_dir):
    data = storage.load_data()
    data["todos"].append({"text": "first", "completed": False})
    storage.save_data(data)
    data["todos"].append({"text": "second", "completed": False})
    storage.save_data(data)

    assert len(storage.load_data()["todos"]) == 2
    backup = json.loads((data_dir / "data.json.bak").read_text())
    assert [t["text"] for t in backup["todos"]] == ["first"]
    assert not (data_dir / "data.json.tmp").exists()


def test_corrupt_file_restores_from_backup(data_dir):
    data = storage.load_data()
    data["todos"].append({"text": "keep me", "completed": False})
    storage.save_data(data)
    storage.save_data(data)

    (data_dir / "data.json").write_text("{not json")
    restored = storage.load_data()

    assert restored["todos"] == [{"text": "keep me", "completed": False}]
    assert list(data_dir.glob("data.corrupt-*.json"))


def test_corrupt_file_without_backup_falls_back_to_defaults(data_dir):
    (data_dir / "data.json").write_text("{not json")
    data = storage.load_data()
    assert data["todos"] == []
    assert list(data_dir.glob("data.corrupt-*.json"))


def test_merge_defaults_fills_missing_nested_keys():
    merged = storage.merge_defaults(
        {"settings": {"current_theme": "Forest"}, "extra": 1},
        {"settings": {"current_theme": "Apricot", "terms": {}}, "todos": []},
    )
    assert merged == {"settings": {"current_theme": "Forest", "terms": {}}, "todos": [], "extra": 1}


def test_load_drops_old_keys_and_fills_timetable(data_dir):
    raw = {
        "reminders": ["old"],
        "settings": {"notification_windows": True, "notification_mac": True},
        "timetable": {"Monday": [{"period": 1, "label": "9.3", "type": "class"}]},
    }
    (data_dir / "data.json").write_text(json.dumps(raw))

    data = storage.load_data()

    assert "reminders" not in data
    assert "notification_windows" not in data["settings"]
    assert "notification_mac" not in data["settings"]
    assert data["settings"]["current_theme"] == "Apricot"
    assert data["timetable"]["Monday"][0]["label"] == "9.3"
    assert data["timetable"]["Friday"] == []


def test_blank_timetable_has_five_periods_a_day():
    timetable = storage.make_blank_timetable()
    assert list(timetable) == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert all([p["period"] for p in day] == [1, 2, 3, 4, 5] for day in timetable.values())


def test_login_and_logout_helpers():
    data = {}
    assert storage.get_current_user(data) is None

    storage.set_current_user(data, {"id": "u1", "username": "dom", "email": "d@x.com", "token": "secret"})
    assert storage.get_current_user(data) == {"id": "u1", "username": "dom", "email": "d@x.com"}
    assert storage.get_last_user_id(data) == "u1"

    storage.logout_current_user(data)
    assert storage.get_current_user(data) is None
    assert data["auth"]["auto_login"] is False
    assert storage.get_last_user_id(data) == "u1"


def test_user_changed_on_this_device():
    data = {}
    assert not storage.user_changed_on_this_device(data, {"id": "u1"})
    storage.set_current_user(data, {"id": "u1"})
    assert not storage.user_changed_on_this_device(data, {"id": "u1"})
    assert storage.user_changed_on_this_device(data, {"id": "u2"})


def test_reset_planner_data_keeps_settings_and_login():
    data = storage.merge_defaults({}, storage.DEFAULT_DATA)
    data["settings"]["current_theme"] = "Forest"
    data["todos"].append({"text": "x", "completed": False})
    storage.set_current_user(data, {"id": "u1"})

    storage.reset_planner_data(data)

    assert data["todos"] == []
    assert data["settings"]["current_theme"] == "Forest"
    assert storage.get_current_user(data)["id"] == "u1"
    assert data["timetable"] == storage.make_blank_timetable()

    storage.reset_planner_data(data, keep_settings=False)
    assert data["settings"]["current_theme"] == "Apricot"


def test_new_account_starts_clean():
    data = storage.merge_defaults({}, storage.DEFAULT_DATA)
    storage.set_current_user(data, {"id": "u1"}, auto_login=False)
    data["setup"]["completed"] = True
    data["app_state"]["last_seen_date"] = "2026-10-29"
    data["weekly_classes"] = {"2026-10-26": {}}

    storage.prepare_new_account_local_state(data)

    assert data["weekly_classes"] == {}
    assert data["setup"]["completed"] is False
    assert data["app_state"]["last_seen_date"] == ""
    assert storage.get_current_user(data)["id"] == "u1"
    assert data["auth"]["auto_login"] is False


def test_change_password_needs_a_signed_in_user():
    assert storage.update_current_user_password({}, "old", "new") == (False, "No signed-in user was found.")


def test_default_data_is_not_mutated_by_loads(data_dir):
    data = storage.load_data()
    data["settings"]["terms"]["2026"] = {"Term 1": {}}
    data["todos"].append({"text": "x", "completed": False})
    assert storage.DEFAULT_DATA["settings"]["terms"] == {}
    assert storage.DEFAULT_DATA["todos"] == []
