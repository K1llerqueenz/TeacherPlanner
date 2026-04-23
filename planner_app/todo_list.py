from __future__ import annotations

from typing import Dict, Any


def add_task(data: Dict[str, Any], text: str) -> None:
    text = text.strip()
    if not text:
        return
    data["todos"].append({"text": text, "completed": False})


def update_task(data: Dict[str, Any], index: int, text: str) -> None:
    if 0 <= index < len(data["todos"]):
        text = text.strip()
        if not text:
            data["todos"].pop(index)
        else:
            data["todos"][index]["text"] = text


def toggle_task(data: Dict[str, Any], index: int) -> None:
    if 0 <= index < len(data["todos"]):
        data["todos"][index]["completed"] = not data["todos"][index].get("completed", False)


def delete_completed_tasks(data: Dict[str, Any]) -> None:
    data["todos"] = [task for task in data.get("todos", []) if not task.get("completed", False)]


def clear_all_tasks(data: Dict[str, Any]) -> None:
    data["todos"] = []