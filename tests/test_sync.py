from copy import deepcopy

from planner_app import storage
from planner_app.sync import (
    CONFLICT,
    NOTHING,
    PULL,
    PUSH,
    apply_server_copy,
    has_unsynced_changes,
    mark_synced,
    merge_server_copy,
    merge_three_way,
    plan_sync,
    planner_payload,
    write_backup,
)


def make_data():
    data = storage.normalise_data(deepcopy(storage.DEFAULT_DATA))
    storage.set_current_user(data, {"id": "u1", "username": "t", "email": "t@x.co"}, token="tok")
    return data


def synced(data, version=1):
    mark_synced(data, "u1", version, planner_payload(data))
    return data


def test_payload_leaves_out_session_and_sync_state():
    data = synced(make_data())
    payload = planner_payload(data)
    assert "auth" not in payload and "sync" not in payload
    assert "todos" in payload


def test_first_sync_with_empty_account_uploads_local_planner():
    data = make_data()
    data["todos"].append({"text": "mark essays"})
    assert plan_sync(data, "u1", 0) == PUSH


def test_first_sync_on_a_blank_computer_downloads():
    assert plan_sync(make_data(), "u1", 3) == PULL


def test_first_sync_with_local_work_and_server_work_asks():
    data = make_data()
    data["setup"]["completed"] = True
    assert plan_sync(data, "u1", 3) == CONFLICT


def test_steady_state_decisions():
    data = synced(make_data(), version=2)
    assert plan_sync(data, "u1", 2) == NOTHING
    assert plan_sync(data, "u1", 3) == PULL

    data["todos"].append({"text": "new"})
    assert has_unsynced_changes(data)
    assert plan_sync(data, "u1", 2) == PUSH
    assert plan_sync(data, "u1", 3) == CONFLICT


def test_signing_in_does_not_count_as_a_change():
    data = synced(make_data())
    storage.set_current_user(data, {"id": "u1", "username": "t", "email": "t@x.co"}, token="new-token")
    assert not has_unsynced_changes(data)


def test_apply_server_copy_keeps_session_and_fills_defaults():
    data = make_data()
    apply_server_copy(data, {"todos": [{"text": "from laptop"}]}, "u1", 4, storage.DEFAULT_DATA)
    assert data["todos"] == [{"text": "from laptop"}]
    assert data["auth"]["token"] == "tok"
    assert data["settings"]["current_theme"] == "Apricot"
    assert set(data["timetable"]) >= {"Monday", "Friday"}
    assert data["sync"]["version"] == 4
    assert plan_sync(data, "u1", 4) == NOTHING


def test_apply_server_copy_ignores_auth_in_server_data():
    data = make_data()
    apply_server_copy(data, {"auth": {"token": "evil"}}, "u1", 1, storage.DEFAULT_DATA)
    assert data["auth"]["token"] == "tok"


def test_write_backup(tmp_path):
    data = make_data()
    path = write_backup(tmp_path, data, "this-computer")
    assert path is not None and path.exists()
    assert "auth" not in path.read_text()


def test_three_way_merge_combines_separate_changes():
    base = {"a": 1, "weeks": {"w1": {"x": 1}}, "todos": []}
    local = {"a": 2, "weeks": {"w1": {"x": 1}, "w2": {"y": 1}}, "todos": []}
    remote = {"a": 1, "weeks": {"w1": {"x": 5}, "w2": {"y": 1}}, "todos": ["t"]}
    merged, conflicts = merge_three_way(base, local, remote)
    assert conflicts == []
    assert merged == {"a": 2, "weeks": {"w1": {"x": 5}, "w2": {"y": 1}}, "todos": ["t"]}


def test_three_way_merge_handles_deletes_and_reports_clashes():
    merged, conflicts = merge_three_way({"a": 1, "b": 1}, {"b": 1}, {"a": 1, "b": 1})
    assert merged == {"b": 1} and conflicts == []
    _, conflicts = merge_three_way({"todos": []}, {"todos": ["home"]}, {"todos": ["school"]})
    assert conflicts == ["/todos"]


def test_merge_server_copy_keeps_both_sides_and_stays_unsynced():
    data = synced(make_data(), version=1)
    server = planner_payload(data)
    server["pd_days"] = ["2026-11-02"]
    data["todos"].append({"text": "local"})

    assert merge_server_copy(data, server, "u1", 2, storage.DEFAULT_DATA) == []
    assert data["pd_days"] == ["2026-11-02"]
    assert data["todos"] == [{"text": "local"}]
    assert data["sync"]["version"] == 2
    assert plan_sync(data, "u1", 2) == PUSH


def test_merge_server_copy_leaves_data_alone_on_conflict():
    data = synced(make_data(), version=1)
    server = planner_payload(data)
    server["todos"] = [{"text": "remote"}]
    data["todos"].append({"text": "local"})
    assert merge_server_copy(data, server, "u1", 2, storage.DEFAULT_DATA) == ["/todos"]
    assert data["todos"] == [{"text": "local"}]
    assert data["sync"]["version"] == 1
