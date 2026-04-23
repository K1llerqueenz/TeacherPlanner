from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

from planner_app.reminders import get_reminder_display_lines
from planner_app.todo_list import (
    add_task,
    toggle_task,
    update_task,
    delete_completed_tasks,
    clear_all_tasks,
)
from planner_app.Ui.base_app import BaseApp
from planner_app.todo_list import delete_completed_tasks


class SidebarMixin(BaseApp):
    def delete_todo(self, index: int) -> None:
        if index < len(self.data.get("todos", [])):
            self.data["todos"].pop(index)
            self.save_and_refresh()

    def clear_all_todos(self) -> None:
        clear_all_tasks(self.data)
        self.todo_edit_mode = False
        self.save_and_refresh()

    def delete_completed_todos(self) -> None:
        delete_completed_tasks(self.data)
        self.todo_edit_mode = False
        self.save_and_refresh()

    def open_todo_menu(self, event=None) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit", command=self.enable_todo_edit_mode)
        menu.add_command(label="Clear all", command=self.clear_all_todos)
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def enable_todo_edit_mode(self) -> None:
        self.todo_edit_mode = True
        self._refresh_todos()

    def disable_todo_edit_mode(self) -> None:
        self.todo_edit_mode = False
        self._refresh_todos()

    def save_todo_edit(self, index: int, widget: tk.Entry) -> None:
        text = widget.get().strip()

        if index < len(self.data.get("todos", [])):
            update_task(self.data, index, text)
        elif text:
            add_task(self.data, text)

        self.todo_edit_mode = False
        self.save_and_refresh()

    def _track_todo_hover(self, event):
        if not hasattr(self, "_todo_delete_windows"):
            return

        for item in self._todo_delete_windows:
            win = item["window"]
            coords = self.sidebar_canvas.coords(win)
            if not coords:
                continue
            x, y = coords
            size = 20
            if x - size < event.x < x + size and y - size < event.y < y + size:
                self.sidebar_canvas.itemconfigure(win, state="normal")
            else:
                self.sidebar_canvas.itemconfigure(win, state="hidden")

    def _build_sidebar(self) -> None:
        self.sidebar_canvas = tk.Canvas(
            self.sidebar,
            width=320,
            height=720,
            bg=self.theme["bg"],
            highlightthickness=0,
            bd=0,
        )
        self.sidebar_canvas.pack(fill="both", expand=True)

        if not hasattr(self, "todo_edit_mode"):
            self.todo_edit_mode = False

        self._draw_sidebar_canvas()
        self.sidebar_canvas.bind("<Motion>", self._track_todo_hover)

    def _draw_sidebar_canvas(self) -> None:
        self.sidebar_canvas.delete("all")
        self.todo_vars = []
        self.todo_entry_widgets = []

        scale = 0.5
        s = lambda x: int(x * scale)

        todo_top = 250
        todo_reminder_gap = 128
        reminder_height = 770

        self._sidebar_layout = {
            "scale": scale,
            "todo_top": todo_top,
            "todo_gap": todo_reminder_gap,
            "reminder_top": todo_top + 560 + todo_reminder_gap,
            "reminder_height": reminder_height,
        }

        self.sidebar_canvas.config(width=s(540), height=s(1450), bg=self.theme["bg"])

        self.sidebar_canvas.create_rectangle(
            s(50), s(todo_top),
            s(600), s(todo_top + 650),
            fill="#e7b3ea",
            outline="",
            tags="todo_bg"
        )
        self.sidebar_canvas.create_rectangle(
            s(20), s(todo_top - 25),
            s(585), s(todo_top + 635),
            fill=self.theme["todo_bg"],
            outline="",
            tags="todo_bg"
        )
        self.sidebar_canvas.create_rectangle(
            s(200), s(todo_top - 65),
            s(425), s(todo_top),
            fill="#e7b3ea",
            outline="",
            tags="todo_bg"
        )
        self.sidebar_canvas.create_text(
            s(300), s(todo_top - 33),
            text="TO-DO",
            font=self._font(14, "bold", "todo_title"),
            fill="black",
            tags="todo_bg"
        )

        dots_btn = ctk.CTkButton(
            self.sidebar_canvas,
            text="⋯",
            font=("Segoe UI", 27),
            fg_color=self.theme["todo_bg"],
            text_color="black",
            hover_color=self.theme["todo_bg"],
            corner_radius=0,
            width=45,
            height=30,
            command=self.open_todo_menu,
        )
        self.sidebar_canvas.create_window(
            s(450),
            s(todo_top - 30),
            window=dots_btn,
            anchor="nw",
            tags="todo_bg"
            )

        reminder_top = self._sidebar_layout["reminder_top"]
        self.sidebar_canvas.create_rectangle(
            s(20),
            s(reminder_top),
            s(600),
            s(reminder_top + reminder_height),
            fill=self.theme["reminder_bg"],
            outline=self.theme["outline"],
            width=3,
            tags="reminder_bg",
        )
        self.sidebar_canvas.create_text(
            s(310),
            s(reminder_top + 40),
            text="REMINDERS",
            font=self._font(int(28 * scale), "bold", "reminder_cards"),
            fill=self.theme["text"],
            tags="reminder_bg",
        )

        self._refresh_todos()
        self._refresh_reminders()

    def _make_todo_underlined_entry(
            self,
            parent: tk.Widget,
            textvariable: tk.StringVar,
            bg_color: str,
            completed: bool = False,
    ) -> tk.Frame:
        wrap = tk.Frame(parent, bg=bg_color, highlightthickness=0, bd=0)

        base_font = tkfont.Font(family="Comic Sans MS", size=13)
        strike_font = tkfont.Font(family="Comic Sans MS", size=13, overstrike=1)

        entry = tk.Entry(
            wrap,
            textvariable=textvariable,
            font=strike_font if completed else base_font,
            bg=bg_color,
            fg="black",
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground="black",
            justify="left",
            readonlybackground=bg_color,
            disabledforeground="black",
        )
        entry.pack(fill="x", padx=0, pady=(0, 3))

        underline = tk.Frame(wrap, bg="#000000", height=2)
        underline.pack(fill="x")

        strike = tk.Frame(wrap, bg="#000000", height=2)
        if completed:
            strike.place(relx=0.0, rely=0.36, relwidth=1.0)

        wrap.entry = entry
        wrap.underline = underline
        wrap.strike = strike
        wrap.base_font = base_font
        wrap.strike_font = strike_font
        return wrap

    def _refresh_todos(self) -> None:
        if not hasattr(self, "sidebar_canvas"):
            return

        self.sidebar_canvas.delete("todo_items")
        self.todo_vars = []
        self.todo_entry_widgets = []
        self._todo_delete_windows = []

        scale = 0.5
        s = lambda x: int(x * scale)
        todo_top = self._sidebar_layout["todo_top"]

        max_rows = 5
        content_top = todo_top + 95
        content_bottom = todo_top + 500
        checkbox_x = 62
        line_x1 = 140
        line_x2 = 500
        entry_width = line_x2 - line_x1
        gap = (content_bottom - content_top) / (max_rows - 1) if max_rows > 1 else 0

        todos = self.data.get("todos", [])[:max_rows]

        purple_fill = "#c78ad9"
        purple_hover = "#c78ad9"

        for i in range(max_rows):
            y = s(content_top + i * gap)

            if i < len(todos):
                item = todos[i]
                text_value = item.get("text", "")
                completed = item.get("completed", False)
            else:
                text_value = ""
                completed = False

            var = tk.BooleanVar(value=completed)
            self.todo_vars.append(var)

            checkbox = ctk.CTkCheckBox(
                self.sidebar_canvas,
                text="",
                width=s(20),
                height=s(20),
                checkbox_width=s(36),
                checkbox_height=s(36),
                corner_radius=9,
                border_width=2,
                fg_color=purple_fill,
                hover_color=purple_hover,
                border_color="black",
                checkmark_color="black",
                bg_color=self.theme["todo_bg"],
                variable=var,
                command=lambda idx=i: self.toggle_todo(idx) if idx < len(self.data["todos"]) else None,
            )
            self.sidebar_canvas.create_window(
                s(checkbox_x),
                y + s(16),
                window=checkbox,
                tags="todo_items"
            )

            entry_var = tk.StringVar(value=text_value)

            entry_wrap = self._make_todo_underlined_entry(
                self.sidebar_canvas,
                entry_var,
                bg_color=self.theme["todo_bg"],
                completed=completed,
            )
            self.sidebar_canvas.create_window(
                s(line_x1),
                y,
                window=entry_wrap,
                width=s(entry_width),
                anchor="nw",
                tags="todo_items"
            )

            entry = entry_wrap.entry

            if i < len(todos):
                if self.todo_edit_mode:
                    entry.configure(state="normal")
                    entry.bind("<Return>", lambda e, idx=i, w=entry: self.save_todo_edit(idx, w))
                    entry.bind("<FocusOut>", lambda e, idx=i, w=entry: self.save_todo_edit(idx, w))
                else:
                    entry.configure(state="readonly")
            else:
                if self.todo_edit_mode:
                    entry.configure(state="normal")
                    entry.bind("<Return>", lambda e, idx=i, w=entry: self.save_todo_edit(idx, w))
                else:
                    entry.configure(state="normal")
                    entry.bind("<Return>", lambda e, w=entry: self.save_todo_edit(len(self.data.get("todos", [])), w))

            delete_btn = tk.Button(
                self.sidebar_canvas,
                text="✕",
                font=("Arial", int(18 * scale), "bold"),
                bg=self.theme["todo_bg"],
                fg="black",
                bd=0,
                activebackground="#f2f7bc",
                cursor="hand2",
                command=lambda idx=i: self.delete_todo(idx),
            )

            delete_window = self.sidebar_canvas.create_window(
                s(line_x2 + 25),
                y + s(8),
                window=delete_btn,
                state="hidden",
                tags="todo_items",
            )
            self._todo_delete_windows.append({"y": y, "window": delete_window})

            self.todo_entry_widgets.append(entry)

    def _refresh_reminders(self) -> None:
        if not hasattr(self, "sidebar_canvas"):
            return

        self.sidebar_canvas.delete("reminder_items")

        scale = 0.5
        s = lambda x: int(x * scale)
        reminder_top = self._sidebar_layout["reminder_top"]

        reminder_lines = get_reminder_display_lines(
            self.data,
            today=getattr(self, "today", None)
        )

        start_y = s(reminder_top + 130)
        gap = s(125)

        if reminder_lines == ["No upcoming reminders"]:
            empty_label = ctk.CTkLabel(
                self.sidebar_canvas,
                text="No upcoming reminders",
                font=self._font(18, "normal", "reminder_cards"),
                fg_color=self.theme["panel"],
                text_color=self.theme["text"],
                corner_radius=18,
                anchor="center",
                justify="center",
                width=s(420),
                height=s(90),
            )
            self.sidebar_canvas.create_window(
                s(310),
                s(reminder_top + 190),
                window=empty_label,
                anchor="n",
                tags="reminder_items"
            )
            return

        for idx, line in enumerate(reminder_lines[:6]):
            card = ctk.CTkLabel(
                self.sidebar_canvas,
                text=line,
                font=self._font(18, "bold", "reminder_cards"),
                text_color=self.theme["text"],
                fg_color=self.theme["panel"],
                corner_radius=18,
                justify="center",
                anchor="center",
                wraplength=s(360),
                padx=18,
                pady=18,
                width=s(420),
                height=s(100),
            )
            self.sidebar_canvas.create_window(
                s(310),
                start_y + idx * gap,
                window=card,
                anchor="n",
                tags="reminder_items"
            )
    def toggle_todo(self, index: int) -> None:
        toggle_task(self.data, index)
        self.save_and_refresh()