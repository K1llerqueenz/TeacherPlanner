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
