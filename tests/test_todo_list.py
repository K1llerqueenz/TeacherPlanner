from planner_app import todo_list


def test_add_update_toggle_and_cleanup():
    data = {"todos": []}
    todo_list.add_task(data, "  mark essays  ")
    todo_list.add_task(data, "   ")
    assert data["todos"] == [{"text": "mark essays", "completed": False}]

    todo_list.toggle_task(data, 0)
    todo_list.add_task(data, "print sheets")
    todo_list.delete_completed_tasks(data)
    assert [t["text"] for t in data["todos"]] == ["print sheets"]

    todo_list.update_task(data, 0, "")
    assert data["todos"] == []


def test_update_task_changes_text():
    data = {"todos": [{"text": "old", "completed": False}]}
    todo_list.update_task(data, 0, "  new  ")
    assert data["todos"] == [{"text": "new", "completed": False}]


def test_out_of_range_index_is_ignored():
    data = {"todos": [{"text": "a", "completed": False}]}
    todo_list.update_task(data, 5, "x")
    todo_list.toggle_task(data, -1)
    assert data["todos"] == [{"text": "a", "completed": False}]


def test_clear_all_tasks():
    data = {"todos": [{"text": "a", "completed": False}, {"text": "b", "completed": True}]}
    todo_list.clear_all_tasks(data)
    assert data["todos"] == []
