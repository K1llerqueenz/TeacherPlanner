from __future__ import annotations

import tkinter as tk
from typing import Any, Dict
from datetime import timedelta

import customtkinter as ctk

from planner_app.storage import save_data
from planner_app.topics import get_week_key, get_class_details, save_class_details
from planner_app.Ui.base_app import BaseApp


class EditorMixin(BaseApp):
    EDITOR_WIDTH = 850
    EDITOR_HEIGHT = 110
    LABEL_EDITOR_HEIGHT = 10
    EDITOR_Y = 20
    EDITOR_RELX = 0.485

    def build_top_editor(self) -> None:
        for child in self.editor_host.winfo_children():
            child.destroy()

        self.editor_frame = ctk.CTkFrame(
            self.root,
            fg_color=self.theme["bg"],
            corner_radius=3,
            border_width=2,
            border_color="#f2a8bc",
            width=self.EDITOR_WIDTH,
            height=self.EDITOR_HEIGHT,
        )
        self.editor_frame.pack_propagate(False)
        self.editor_frame.grid_propagate(False)

        self.editor_container = tk.Frame(self.editor_frame, bg=self.theme["bg"])
        self.editor_container.pack(fill="both", expand=True, padx=10, pady=6)

        self.editor_widgets = {}
        self.clear_top_editor()

    def clear_top_editor(self) -> None:
        if hasattr(self, "editor_container"):
            for child in self.editor_container.winfo_children():
                child.destroy()

        if hasattr(self, "editor_frame"):
            self.editor_frame.place_forget()

        self.editor_state = None
        self.editor_widgets = {}
        self.editor_visible = False

    def open_top_editor(self, day_name: str, entry: Dict[str, Any]) -> None:
        self.editor_frame.configure(
            width=self.EDITOR_WIDTH,
            height=self.EDITOR_HEIGHT,
        )
        self.editor_frame.place(
            in_=self.root,
            relx=self.EDITOR_RELX,
            y=self.EDITOR_Y,
            anchor="n",
        )

        self.save_top_editor_if_needed()

        for child in self.editor_container.winfo_children():
            child.destroy()

        week_key = get_week_key(self.view_date)
        details = get_class_details(self.data, week_key, day_name, entry["period"], entry["label"])

        week_monday = self.view_date - timedelta(days=self.view_date.weekday())
        day_index = list(self.data["timetable"].keys()).index(day_name)
        target_date = week_monday + timedelta(days=day_index)

        self.editor_state = {
            "day_name": day_name,
            "entry": entry,
            "week_key": week_key,
            "target_date": target_date,
            "type": "label" if entry["type"] == "label" else "class",
        }
        self.editor_visible = True
        self.editor_widgets = {}

        close_btn = tk.Button(
            self.editor_frame,
            text="✕",
            command=self.close_top_editor,
            bg=self.theme["bg"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            font=self._font(12, "bold"),
            cursor="hand2",
        )
        close_btn.place(relx=1.0, x=-6, y=4, anchor="ne")

        if self.editor_state["type"] == "class":
            self._build_class_editor(details)
        else:
            self._build_label_editor(entry, details)

        self.bind_editor_shortcuts()

    def _build_class_editor(self, details: Dict[str, Any]) -> None:
        self.editor_container.grid_columnconfigure(0, weight=0)
        self.editor_container.grid_columnconfigure(1, weight=0)
        self.editor_container.grid_rowconfigure(0, weight=0)

        left = tk.Frame(self.editor_container, bg=self.theme["bg"])
        left.grid(row=0, column=0, sticky="nw", padx=(0, 10))

        right = tk.Frame(self.editor_container, bg=self.theme["bg"])
        right.grid(row=0, column=1, sticky="nsew")

        left.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        label_pad_y = (0, 2)
        widget_pad_y = (0, 6)

        # --- row map: easy to edit later ---
        LEFT_TITLE_LABEL_ROW = 0
        LEFT_TITLE_ENTRY_ROW = 1
        LEFT_PRINTED_ROW = 2

        RIGHT_NOTES_LABEL_ROW = 2
        RIGHT_NOTES_BOX_ROW = 3

        topic_text = ""
        students = 0

        if self.editor_state:
            entry = self.editor_state["entry"]
            day_name = self.editor_state["day_name"]
            period = entry["period"]
            class_name = entry["label"]
            target_date = self.editor_state["target_date"]

            students = self.get_students_for_lesson(day_name, period)
            topic_text = self.get_topic_for_class_on_date(class_name, target_date)

        tk.Label(
            left,
            text="Lesson Topic:",
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=self._font(12)
        ).grid(row=LEFT_TITLE_LABEL_ROW, column=0, sticky="w", pady=label_pad_y)

        title_entry = tk.Entry(left, font=self._font(12), width=30)
        title_entry.grid(row=LEFT_TITLE_ENTRY_ROW, column=0, sticky="w", pady=widget_pad_y)
        title_entry.insert(0, topic_text)

        printed_var = tk.BooleanVar(value=bool(details.get("printed_resources", False)))
        printed_box = tk.Checkbutton(
            left,
            text="Print Resources Needed: " + str(students),
            variable=printed_var,
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=self._font(12),
            anchor="w",
        )
        printed_box.grid(row=LEFT_PRINTED_ROW, column=0, sticky="w", pady=widget_pad_y)

        tk.Label(
            right,
            text="Tasks:",
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=self._font(12)
        ).grid(row=RIGHT_NOTES_LABEL_ROW, column=0, sticky="w", pady=label_pad_y)

        notes_text = tk.Text(
            right,
            height=3,
            width=82,
            font=self._font(12),
            wrap="word"
        )
        notes_text.grid(row=RIGHT_NOTES_BOX_ROW, column=0, sticky="ew", pady=widget_pad_y)
        notes_text.insert("0.0", details.get("notes", ""))

        self.editor_widgets["topic"] = title_entry
        self.editor_widgets["printed_resources"] = printed_var
        self.editor_widgets["notes"] = notes_text

        title_entry.focus_set()

    def _build_label_editor(self, entry: Dict[str, Any], details: Dict[str, Any]) -> None:
        self.editor_container.grid_columnconfigure(0, weight=0)
        self.editor_container.grid_columnconfigure(1, weight=0)
        self.editor_container.grid_rowconfigure(0, weight=0)

        left = tk.Frame(self.editor_container, bg=self.theme["bg"])
        left.grid(row=0, column=0, sticky="nw", padx=(0, 10))

        right = tk.Frame(self.editor_container, bg=self.theme["bg"])
        right.grid(row=0, column=1, sticky="nsew")

        left.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        label_pad_y = (0, 2)
        widget_pad_y = (0, 6)

        # --- row map ---
        LEFT_TYPE_LABEL_ROW = 0
        LEFT_TYPE_ENTRY_ROW = 1

        RIGHT_NOTES_LABEL_ROW = 0
        RIGHT_NOTES_BOX_ROW = 1

        def type_label() -> str:
            return "Type of DOTT:" if entry["label"].strip().upper() == "DOTT" else "Meeting Agenda:"

        tk.Label(
            left,
            text=type_label(),
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=self._font(12)
        ).grid(row=LEFT_TYPE_LABEL_ROW, column=0, sticky="w", pady=label_pad_y)

        dott_entry = tk.Entry(left, font=self._font(12), width=30)
        dott_entry.grid(row=LEFT_TYPE_ENTRY_ROW, column=0, sticky="w", pady=widget_pad_y)
        dott_entry.insert(0, details.get("dott_type", ""))

        tk.Label(
            right,
            text="Notes:",
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=self._font(12)
        ).grid(row=RIGHT_NOTES_LABEL_ROW, column=0, sticky="w", pady=label_pad_y)

        notes_text = tk.Text(
            right,
            height=3,
            width=82,
            font=self._font(12),
            wrap="word"
        )
        notes_text.grid(row=RIGHT_NOTES_BOX_ROW, column=0, sticky="ew", pady=widget_pad_y)
        notes_text.insert("1.0", details.get("notes", ""))

        self.editor_widgets["dott_type"] = dott_entry
        self.editor_widgets["notes"] = notes_text

        dott_entry.focus_set()
    def bind_editor_shortcuts(self) -> None:
        for widget in self.editor_widgets.values():
            if isinstance(widget, tk.Entry):
                widget.bind("<Return>", lambda e, w=widget: self.save_and_close_top_editor())
            elif isinstance(widget, tk.Text):
                widget.bind("<Control-Return>", lambda e, w=widget: self.save_and_close_top_editor())

    def _get_topic_keys_for_date(self, target_date):
        result = self.get_term_week_for_date(target_date)
        if not result:
            return None

        year_value, term_key, week_key = result
        if not year_value or not term_key or not week_key:
            return None

        day_key = target_date.strftime("%A")
        return year_value, term_key, week_key, day_key

    def get_topic_for_slot(
            self,
            class_name: str,
            year_value: str,
            term_key: str,
            week_key: str,
            day_key: str,
    ) -> str:
        topic_overview = self.data.setdefault("topic_overview", {})
        class_key = class_name.strip()

        return (
            topic_overview.get(class_key, {})
            .get(str(year_value), {})
            .get(term_key, {})
            .get(week_key, {})
            .get(day_key, "")
        )

    def set_topic_for_slot(
            self,
            class_name: str,
            year_value: str,
            term_key: str,
            week_key: str,
            day_key: str,
            topic_text: str,
    ) -> None:
        topic_overview = self.data.setdefault("topic_overview", {})
        class_key = class_name.strip()
        year_value = str(year_value)
        clean_text = topic_text.strip()

        topic_overview.setdefault(class_key, {})
        topic_overview[class_key].setdefault(year_value, {})
        topic_overview[class_key][year_value].setdefault(term_key, {})
        topic_overview[class_key][year_value][term_key].setdefault(week_key, {})

        if clean_text:
            topic_overview[class_key][year_value][term_key][week_key][day_key] = clean_text
        else:
            topic_overview[class_key][year_value][term_key][week_key].pop(day_key, None)

            if not topic_overview[class_key][year_value][term_key][week_key]:
                topic_overview[class_key][year_value][term_key].pop(week_key, None)
            if not topic_overview[class_key][year_value][term_key]:
                topic_overview[class_key][year_value].pop(term_key, None)
            if not topic_overview[class_key][year_value]:
                topic_overview[class_key].pop(year_value, None)
            if not topic_overview[class_key]:
                topic_overview.pop(class_key, None)

    def get_topic_for_class_on_date(self, class_name: str, target_date) -> str:
        keys = self._get_topic_keys_for_date(target_date)
        if not keys:
            return ""

        year_value, term_key, week_key, day_key = keys
        return self.get_topic_for_slot(class_name, year_value, term_key, week_key, day_key)

    def set_topic_for_class_on_date(self, class_name: str, target_date, topic_text: str) -> None:
        keys = self._get_topic_keys_for_date(target_date)
        if not keys:
            return

        year_value, term_key, week_key, day_key = keys
        self.set_topic_for_slot(class_name, year_value, term_key, week_key, day_key, topic_text)
    def save_top_editor_if_needed(self) -> None:
        if not self.editor_state:
            return

        day_name = self.editor_state["day_name"]
        entry = self.editor_state["entry"]
        week_key = self.editor_state["week_key"]

        details: Dict[str, Any] = {}
        for key, widget in self.editor_widgets.items():
            if isinstance(widget, tk.Entry):
                details[key] = widget.get().strip()
            elif isinstance(widget, tk.Text):
                details[key] = widget.get("1.0", "end").strip()
            elif isinstance(widget, tk.BooleanVar):
                details[key] = widget.get()

        if self.editor_state["type"] == "class":
            target_date = self.editor_state["target_date"]
            topic_text = details.pop("topic", "").strip()
            self.set_topic_for_class_on_date(entry["label"], target_date, topic_text)

        save_class_details(self.data, week_key, day_name, entry["period"], entry["label"], details)
        save_data(self.data)
        self.refresh_all()

    def save_and_close_top_editor(self) -> None:
        self.save_top_editor_if_needed()
        self.clear_top_editor()

    def close_top_editor(self) -> None:
        self.save_top_editor_if_needed()
        self.editor_frame.place_forget()
        self.editor_visible = False
