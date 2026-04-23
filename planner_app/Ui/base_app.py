import customtkinter as ctk
from typing import Any, Optional
import tkinter as tk

from planner_app.storage import save_data
from planner_app.settings import get_theme
from planner_app.todo_list import delete_completed_tasks


class BaseApp(ctk.CTk):
    theme: dict[str, str]
    data: dict[str, Any]
    settings: dict[str, Any]
    local_fonts: list[str]

    topic_prompt_queue: list[dict[str, Any]]
    topic_prompt_index: int

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.topic_prompt_queue = []
        self.topic_prompt_index = 0

    def _font(self, size: int, weight: str = "normal", section: Optional[str] = None) -> tuple:
        if section:
            family = self.settings.get("font_sections", {}).get(
                section,
                self.settings.get("font_family", "Segoe UI")
            )
        else:
            family = self.settings.get("font_family", "Segoe UI")
        return family, size, weight

    def apply_theme_to_all(self):
        self.configure(fg_color=self.theme["bg"])

        for widget in self.winfo_children():
            self._refresh_widget_theme(widget)

    def _refresh_widget_theme(self, widget):
        try:
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(fg_color=self.theme["panel"])

            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(
                    fg_color="transparent",
                    text_color=self.theme["text"]
                )

            elif isinstance(widget, ctk.CTkButton):
                widget.configure(
                    fg_color=self.theme["accent"],
                    hover_color=self.theme["accent_hover"],
                    text_color=self.theme["button_text"]
                )

            elif isinstance(widget, tk.Text):
                widget.configure(
                    bg=self.theme["entry_bg"],
                    fg=self.theme["text"],
                    insertbackground=self.theme["text"]
                )

        except Exception:
            pass

        for child in widget.winfo_children():
            self._refresh_widget_theme(child)

    def open_overlay(self) -> ctk.CTkFrame:
        self.close_overlay()
        overlay = ctk.CTkFrame(self, fg_color="#000000")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        overlay.bind("<Button-1>", lambda e: "break")
        self.bind_all("<Escape>", lambda e: self.close_overlay())
        self.current_overlay = overlay
        return overlay

    def close_overlay(self) -> None:
        self.unbind_all("<Escape>")
        overlay = getattr(self, "current_overlay", None)
        if overlay is not None and overlay.winfo_exists():
            overlay.destroy()
        self.current_overlay = None

    def save_and_refresh(self) -> None:
        save_data(self.data)
        self.refresh_all()

    def refresh_all(self) -> None:
        self.theme = get_theme(self.settings)
        self.configure(fg_color=self.theme["bg"])

        if hasattr(self, "content") and self.content.winfo_exists():
            try:
                self.content.configure(fg_color=self.theme["bg"])
            except Exception:
                self.content.configure(bg=self.theme["bg"])

        if hasattr(self, "planner_frame") and self.planner_frame.winfo_exists():
            try:
                self.planner_frame.configure(fg_color=self.theme["bg"])
            except Exception:
                self.planner_frame.configure(bg=self.theme["bg"])

        if hasattr(self, "sidebar") and self.sidebar.winfo_exists():
            try:
                self.sidebar.configure(fg_color=self.theme["bg"])
            except Exception:
                self.sidebar.configure(bg=self.theme["bg"])

        if hasattr(self, "days_frame") and self.days_frame.winfo_exists():
            try:
                self.days_frame.configure(fg_color=self.theme["bg"])
            except Exception:
                self.days_frame.configure(bg=self.theme["bg"])

        self._refresh_header()
        self._refresh_days()
        self._refresh_todos()
        self._refresh_reminders()

    def get_students_for_lesson(self, day_name: str, period: int) -> int:
        for lesson in self.data.get("timetable", {}).get(day_name, []):
            if lesson.get("period") == period:
                return lesson.get("students", 0)
        return 0

    def cleanup_completed_todos_for_new_day(self) -> None:
        app_state = self.data.setdefault("app_state", {})
        today_str = self.today.isoformat()
        last_seen_date = app_state.get("last_seen_date", "")

        changed = False

        if last_seen_date and last_seen_date != today_str:
            before = len(self.data.get("todos", []))
            delete_completed_tasks(self.data)
            after = len(self.data.get("todos", []))
            changed = before != after

        if last_seen_date != today_str:
            app_state["last_seen_date"] = today_str
            changed = True

        if changed:
            save_data(self.data)