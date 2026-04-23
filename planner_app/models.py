from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ToDoItem:
    text: str
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReminderItem:
    title: str
    class_name: str
    due_date: str
    kind: str = "assignment"  # assignment or event
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClassDetails:
    class_name: str
    topic: str = ""
    printed_resources: bool = False
    notes: str = ""
    room: str = ""
    homework: str = ""
    priority: str = ""
    assignment_name: str = ""
    assignment_due_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
