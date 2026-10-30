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
