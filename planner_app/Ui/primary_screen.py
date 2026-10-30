from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import customtkinter as ctk
import sys
from pathlib import Path

from planner_app.Ui.login_mixin import LoginMixin
from planner_app.Ui.setup_mixin import SetupMixin
from planner_app.terms import HARDCODED_TERMS, get_day_block_label
from planner_app.Ui.editor_mixin import EditorMixin
from planner_app.Ui.base_app import BaseApp
from planner_app.Ui.popups_mixin import PopupsMixin
from planner_app.reminders import parse_date
from planner_app.settings import get_theme, load_local_fonts
from planner_app.Ui.settings_mixin import SettingsMixin
from planner_app.Ui.sidebar_mixin import SidebarMixin
from planner_app.storage import load_data, save_data, has_users, get_current_user
from planner_app.timetable import DAYS
from planner_app.topics import (
    get_class_details,
    get_missing_topics_for_week,
    get_week_key,
    ensure_week_records,
    should_show_friday_prompt,
    should_show_monday_prompt,
)


class PrimaryScreen(LoginMixin, SetupMixin, EditorMixin, SidebarMixin, PopupsMixin, SettingsMixin, BaseApp):
    def __init__(self) -> None:
        super().__init__()
        self.title("Teacher Planner")



        def resource_path(relative_path: str) -> str:
            try:
                base_path = Path(sys._MEIPASS)
            except Exception:
                base_path = Path(__file__).resolve().parents[2]
            return str(base_path / relative_path)

        icon_path = resource_path("planner_app/assets/favicon.ico")

        try:
            self.iconbitmap(icon_path)
        except Exception as e:
            print("Icon error:", e)

        self.data = load_data()
        self.day_outer_frames = {}
        self.editor_state: Optional[Dict[str, Any]] = None
        self.editor_widgets: Dict[str, Any] = {}
        self.editor_visible = False
        self.local_fonts = load_local_fonts()
        self.settings = self.data["settings"]
        self.theme = get_theme(self.settings)
        self.today = date.today()
        self.view_date = self.today
        self.cleanup_completed_todos_for_new_day()
        self.topic_prompt_queue: List[Dict[str, Any]] = []
        self.topic_prompt_index = 0
        self.current_overlay: Optional[tk.Frame] = None
        self.todo_vars: List[tk.BooleanVar] = []

        self._set_initial_geometry()
        self._build_styles()

        self._route_on_startup()

    def _set_initial_geometry(self) -> None:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width_ratio = float(self.settings.get("window_width_ratio", 0.92))
        height_ratio = float(self.settings.get("window_height_ratio", 0.9))
        width = max(1180, int(screen_w * width_ratio))
        height = max(760, int(screen_h * height_ratio))
        x = max(30, (screen_w - width) // 2)
        y = max(20, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1180, 760)

    def get_class_colour(self, class_name: str) -> str:
        fallback = self.theme.get("class_fill", self.theme.get("panel", "#ffffff"))
        return self.settings.get("class_colours", {}).get(class_name, fallback)

    def set_class_colour(self, class_name: str, colour: str) -> None:
        self.settings.setdefault("class_colours", {})
        self.settings["class_colours"][class_name] = colour

    def get_label_colour(self, label_name: str) -> str:
        fallback = self.theme.get("label_fill", "#fca95b")
        key = label_name.strip().upper()
        return self.settings.get("label_colours", {}).get(key, fallback)

    def set_label_colour(self, label_name: str, colour: str) -> None:
        self.settings.setdefault("label_colours", {})
        key = label_name.strip().upper()
        self.settings["label_colours"][key] = colour

    def get_term_week_for_date(self, target_date: date):
        year = str(target_date.year)

        # First try user/custom term settings
        terms_source = self.settings.get("terms", {})
        term_settings = terms_source.get(year, {})

        # Fallback to hardcoded terms if settings are missing
        if not term_settings:
            term_settings = HARDCODED_TERMS.get(year, {})

        for term_name in ["Term 1", "Term 2", "Term 3", "Term 4"]:
            term_data = term_settings.get(term_name, {})
            start_text = term_data.get("start", "")
            end_text = term_data.get("end", "")

            if not start_text or not end_text:
                continue

            start_date = parse_date(start_text)
            end_date = parse_date(end_text)
            if start_date is None or end_date is None:
                continue

            if start_date <= target_date <= end_date:
                week_num = ((target_date - start_date).days // 7) + 1
                return year, term_name, f"Week {week_num}"

        return None, None, None

    def _route_on_startup(self) -> None:
        current_user = get_current_user(self.data)

        if current_user and self.data.get("auth", {}).get("auto_login", True):
            setup_info = self.data.get("setup", {})
            if not setup_info.get("completed", False):
                self.show_first_run_setup()
            else:
                self.start_main_planner()
            return

        if not has_users(self.data):
            self.show_create_account_screen()
        else:
            self.show_login_screen()

    def get_assignments_for_class_on_date(self, class_name: str, target_date: date, period: int):
        year, term_name, week_name = self.get_term_week_for_date(target_date)
        if not year or not term_name or not week_name:
            return []

        # Build ordered list of ALL lessons for that class in the week
        lesson_counter = 0
        lesson_map = {}  # (day, period) -> lesson number

        for day in DAYS:
            for lesson in self.data.get("timetable", {}).get(day, []):
                if lesson.get("type") == "class" and lesson.get("label") == class_name:
                    lesson_counter += 1
                    lesson_map[(day, lesson.get("period"))] = lesson_counter

        # Get current day + lesson number
        day_name = target_date.strftime("%A")
        lesson_number = lesson_map.get((day_name, period))

        if not lesson_number:
            return []

        lesson_name = f"Lesson {lesson_number}"

        return [
            item for item in self.data.get("assignments", [])
            if item.get("class") == class_name
            and item.get("year") == year
            and item.get("term") == term_name
            and item.get("week") == week_name
            and item.get("lesson") == lesson_name
        ]

    def class_has_assignment_on_date(self, class_name: str, target_date: date, period: int) -> bool:
        return len(self.get_assignments_for_class_on_date(class_name, target_date, period)) > 0

    def _build_styles(self) -> None:
        self.configure(bg=self.theme["bg"])

    def start_main_planner(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        self.day_outer_frames = {}
        self.editor_state = None
        self.editor_widgets = {}
        self.editor_visible = False
        self.current_overlay = None
        self.todo_vars = []

        self.settings = self.data["settings"]
        self.theme = get_theme(self.settings)
        self.configure(bg=self.theme["bg"], fg_color=self.theme["bg"])

        self._build_ui()
        self.refresh_all()
        self._schedule_tick(1000)

    def _build_ui(self) -> None:
        self.root = tk.Frame(self, bg=self.theme["bg"])
        self.root.pack(fill="both", expand=True, padx=16, pady=12)

        self.main_row = tk.Frame(self.root, bg=self.theme["bg"])
        self.main_row.pack(fill="both", expand=True)

        self.left_main = tk.Frame(self.main_row, bg=self.theme["bg"])
        self.left_main.pack(side="left", fill="both", expand=True)

        self.sidebar = tk.Frame(self.main_row, bg=self.theme["bg"], width=340)
        self.sidebar.pack(side="right", fill="y", padx=(14, 0))
        self.sidebar.pack_propagate(False)

        top_area = tk.Frame(self.left_main, bg=self.theme["bg"])
        top_area.pack(fill="x", pady=(0, 2))

        top_header = tk.Frame(top_area, bg=self.theme["bg"])
        top_header.pack(fill="x", pady=(0, 0))

        self.title_label = tk.Label(top_header, text="Term ? Week ?",
                                    font=self._font(28, "bold", "term_title"),
                                    bg=self.theme["bg"], fg=self.theme["accent"], anchor="w")
        self.title_label.pack(side="left", anchor="w", pady=(30, 0))

        self.settings_button = tk.Button(self, text="☰", font=self._font(18, "bold"),
                                         bg=self.theme["bg"], fg=self.theme["accent"],
                                         relief="flat", bd=0, activebackground=self.theme["bg"],
                                         activeforeground=self.theme["accent"], command=self.open_settings_popup,
                                         cursor="hand2", padx=8, pady=2)
        self.settings_button.place(in_=self, relx=1.0, x=-10, y=10, anchor="ne")
        self.settings_button.lift()

        self.editor_host = tk.Frame(top_area, bg=self.theme["bg"], height=78)
        self.editor_host.pack(fill="x", pady=(4, 0))
        self.editor_host.pack_propagate(False)
        self.build_top_editor()

        self.content = tk.Frame(self.left_main, bg=self.theme["bg"])
        self.content.pack(fill="both", expand=True)

        self.planner_frame = tk.Frame(self.content, bg=self.theme["bg"])
        self.planner_frame.pack(fill="both", expand=True)

        self.days_frame = tk.Frame(self.planner_frame, bg=self.theme["panel"])
        self.days_frame.pack(fill="both", expand=True)

        self.day_columns = {}
        self.day_cards = {}
        self.day_header_labels = {}

        for day_name in DAYS:
            col_wrap = ctk.CTkFrame(self.days_frame, fg_color=self.theme["panel"], corner_radius=0)
            col_wrap.pack(side="left", fill="both", expand=True, padx=7)

            col = ctk.CTkFrame(
                col_wrap,
                corner_radius=9,
                fg_color=self.theme["panel"],
                border_width=0
            )
            col.pack(fill="both", expand=True, padx=2, pady=(12, 6))

            day_header = ctk.CTkLabel(
                col_wrap,
                text=day_name,
                corner_radius=12,
                fg_color="#ead7dc",  # slightly different from background
                text_color="#111111",
                font=self._font(14, "bold", "day_headers"),
                height=42,
                padx=18
            )
            day_header.place(relx=0.5, y=0, anchor="n")
            day_header.lift()

            self.day_header_labels[day_name] = day_header

            card_holder = ctk.CTkFrame(col, fg_color="transparent")
            card_holder.pack(fill="both", expand=True, padx=8, pady=(42, 10))

            self.day_columns[day_name] = card_holder
            self.day_outer_frames[day_name] = col
            self.day_cards[day_name] = []
        self._build_sidebar()

        nav_bar = tk.Frame(self.root, bg=self.theme["bg"])
        nav_bar.pack(fill="x", pady=(8, 0))

        self.prev_button = tk.Button(nav_bar, text="⬅", font=self._font(22, "bold"),
                                     bg=self.theme["bg"], fg=self.theme["accent"],
                                     bd=0, command=self.go_prev_week, cursor="hand2")
        self.prev_button.pack(side="left")
        self.bind("<Left>", lambda e: self.go_prev_week())
        self.prev_button.bind("<Leave>", lambda e: self.prev_button.config(fg=self.theme["accent"]))

        self.next_button = tk.Button(nav_bar, text="➡", font=self._font(22, "bold"),
                                     bg=self.theme["bg"], fg=self.theme["accent"],
                                     bd=0, command=self.go_next_week, cursor="hand2")
        self.next_button.pack(side="right")
        self.bind("<Right>", lambda e: self.go_next_week())

    def _refresh_header(self) -> None:
        term_text = self.get_term_week_text(self.view_date)
        self.title_label.config(text=term_text, bg=self.theme["bg"], fg=self.theme["accent"],
                                font=self._font(30, "bold", "term_title"))
        self.prev_button.config(bg=self.theme["bg"], fg=self.theme["accent"], font=self._font(24, "bold"))
        self.next_button.config(bg=self.theme["bg"], fg=self.theme["accent"], font=self._font(24, "bold"))
        self.settings_button.config(bg=self.theme["bg"], fg=self.theme["accent"], font=self._font(18, "bold"),
                                    activebackground=self.theme["bg"], activeforeground=self.theme["accent"])

    def _normalise_pd_entry(self, entry) -> dict | None:
        if isinstance(entry, str):
            return {"date": entry, "type": "full"}

        if isinstance(entry, dict):
            date_text = entry.get("date", "")
            entry_type = entry.get("type", "full")

            if entry_type == "first_periods":
                count = int(entry.get("count", 0) or 0)
                return {"date": date_text, "type": "first_periods", "count": count}

            if entry_type == "selected_periods":
                periods = sorted({
                    int(p) for p in entry.get("periods", [])
                    if str(p).isdigit() and 1 <= int(p) <= 5
                })
                return {"date": date_text, "type": "selected_periods", "periods": periods}

            return {"date": date_text, "type": "full"}

        return None

    def get_pd_entries_for_date(self, target_date: date) -> list[dict]:
        iso = target_date.isoformat()
        results = []

        for entry in self.data.get("pd_days", []):
            norm = self._normalise_pd_entry(entry)
            if norm and norm.get("date") == iso:
                results.append(norm)

        return results

    def is_full_pd_day(self, target_date: date) -> bool:
        return any(
            entry.get("type") == "full"
            for entry in self.get_pd_entries_for_date(target_date)
        )

    def is_pd_period(self, target_date: date, period: int) -> bool:
        for entry in self.get_pd_entries_for_date(target_date):
            entry_type = entry.get("type")

            if entry_type == "full":
                return True

            if entry_type == "first_periods":
                if period <= int(entry.get("count", 0) or 0):
                    return True

            if entry_type == "selected_periods":
                if period in entry.get("periods", []):
                    return True

        return False

    def get_blocked_day_info(self, target_date: date) -> dict | None:
        if self.is_full_pd_day(target_date):
            return {
                "label": "PD Day\nNo classes scheduled",
                "bg": self.theme.get("pd_day_bg", "#E6CBA8"),
                "border": "#a68a64",
            }

        label = get_day_block_label(target_date, self.settings.get("terms", {}))
        if not label:
            return None

        if label == "Public Holiday":
            return {
                "label": "Public Holiday\nNo classes scheduled",
                "bg": self.theme.get("public_holiday_bg", "#D9C2E9"),
                "border": "#9d84b5",
            }

        if label == "School Holidays":
            col = self.theme["panel"],
            return {
                "label": "School Holidays\nNo classes scheduled",
                "bg": self.theme.get("school_holiday_bg", "#BFDCC3"),
                "border": "#7ea98a",
            }

        return {
            "label": "School Holidays\nPublic Holiday\nNo classes scheduled",
            "bg": self.theme.get("school_holiday_bg", "#BFDCC3"),
            "border": "#7ea98a",
        }

    def _refresh_days(self) -> None:
        week_monday = self.view_date - timedelta(days=self.view_date.weekday())
        current_week_monday = self.today - timedelta(days=self.today.weekday())

        for idx, day_name in enumerate(DAYS, start=1):
            holder = self.day_columns[day_name]
            outer = self.day_outer_frames[day_name]
            header_label = self.day_header_labels[day_name]

            day_date = week_monday + timedelta(days=idx - 1)

            is_today = day_date == self.today and week_monday == current_week_monday
            blocked_info = self.get_blocked_day_info(day_date)

            try:
                date_text = day_date.strftime("%-d %b")
            except ValueError:
                date_text = day_date.strftime("%d %b").lstrip("0")

            for child in holder.winfo_children():
                child.destroy()

            holder.pack_forget()
            holder.pack(fill="both", expand=True, padx=8, pady=(42, 10))

            for row in range(10):
                holder.grid_rowconfigure(row, weight=0, minsize=0)
            for col in range(3):
                holder.grid_columnconfigure(col, weight=0, minsize=0)

            holder.grid_columnconfigure(0, weight=1)

            if blocked_info:
                outer.configure(
                    fg_color=blocked_info["bg"],
                    border_color=blocked_info["border"],
                    border_width=6 if is_today else 4,
                )

                header_label.configure(
                    text=f"{day_name}\n{date_text}",
                    text_color="#111111",
                    fg_color="#f3d9df",
                    font=self._font(14, "bold", "day_headers")
                )

                holder.configure(fg_color="transparent")
                holder.grid_rowconfigure(0, weight=1)

                blocked_card = tk.Frame(
                    holder,
                    bg=blocked_info["bg"],
                    relief="flat",
                    padx=8,
                    pady=8
                )
                blocked_card.grid(row=0, column=0, sticky="nsew", pady=6)

                tk.Label(
                    blocked_card,
                    text=blocked_info["label"],
                    bg=blocked_info["bg"],
                    fg="#444444",
                    font=self._font(11, "bold", "class_cards"),
                    justify="center"
                ).place(relx=0.5, rely=0.5, anchor="center")

                continue

            outer.configure(
                fg_color=self.theme["panel"],
                border_color=self.theme["accent"] if is_today else self.theme.get(
                    f"{day_name} Border",
                    self.theme["outline"]
                ),
                border_width=6 if is_today else 4,
            )

            header_label.configure(
                text=f"{day_name}\n{date_text}",
                text_color="#111111",
                fg_color="#f3d9df",
                font=self._font(14, "bold", "day_headers")
            )

            holder.configure(fg_color="transparent")

            week_key = get_week_key(self.view_date)
            day_entries = self.data["timetable"][day_name]

            for row_index in range(len(day_entries)):
                holder.grid_rowconfigure(row_index, weight=1)

            for row_index, entry in enumerate(day_entries):
                pady = (6, 18) if row_index in (1, 3) else 6
                self._make_class_card(holder, week_key, day_name, entry, row_index, pady, day_date)

            holder.update_idletasks()

    def _make_class_card(self, parent, week_key, day_name, entry, row_index, pady_value, day_date):
        class_bg = self.get_class_colour(entry["label"])
        parent.grid_rowconfigure(row_index, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        if entry["type"] == "class":
            is_pd_session = self.is_pd_period(day_date, entry["period"])
            details = get_class_details(self.data, week_key, day_name, entry["period"], entry["label"])
            topic = self.get_topic_for_class_on_date(entry["label"], day_date)
            printed_value = bool(details.get("printed_resources", False))

            if is_pd_session:
                class_bg = "#d3d3d3"
                display_text = "PD Session"
            else:
                class_bg = self.get_class_colour(entry["label"])
                display_text = entry["label"]
                if topic:
                    display_text += f"\n{topic}"

            card = tk.Frame(
                parent,
                bg=class_bg,
                relief="solid",
                highlightbackground="black" if printed_value and not is_pd_session else class_bg,
                highlightthickness=1 if printed_value and not is_pd_session else 0,
                padx=8,
                pady=8
            )
            card.grid(row=row_index, column=0, sticky="nsew", pady=pady_value)

            main_button = tk.Button(
                card,
                text=display_text,
                font=self._font(9, "bold", "class_cards"),
                justify="center",
                wraplength=135,
                bg=class_bg,
                fg=self.theme["text"],
                activebackground=class_bg,
                activeforeground=self.theme["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
                command=(lambda e=entry: self.open_top_editor(day_name, e)) if not is_pd_session else (lambda: None),
                padx=4,
                pady=4
            )

            main_button.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)

            assignments = [] if is_pd_session else self.get_assignments_for_class_on_date(entry["label"], day_date,
                                                                                          entry["period"])

            if assignments:
                tooltip_text = "\n".join(a.get("title", "") for a in assignments if a.get("title"))

                dot = tk.Canvas(card, width=14, height=14, bg=class_bg, highlightthickness=0)
                dot.place(relx=1.0, rely=1.0, x=-8, y=-8, anchor="se")
                dot.create_oval(3, 3, 14, 14, fill=self.theme["accent"], outline="")

                tooltip = tk.Label(
                    card,
                    text=tooltip_text,
                    bg="#fff8dc",
                    fg=self.theme["text"],
                    relief="solid",
                    bd=1,
                    padx=6,
                    pady=3,
                    font=self._font(12),
                    justify="left"
                )

                def show_tooltip(_event):
                    if tooltip_text:
                        tooltip.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
                        tooltip.tkraise()

                def hide_tooltip(_event):
                    tooltip.place_forget()

                dot.bind("<Enter>", show_tooltip)
                dot.bind("<Leave>", hide_tooltip)

        elif entry["type"] == "label":
            label_bg = self.get_label_colour(entry["label"])

            card = tk.Frame(
                parent,
                bg=label_bg,
                relief="flat",
                padx=8,
                pady=8
            )
            card.grid(row=row_index, column=0, sticky="nsew", pady=pady_value)

            display_text = entry["label"]

            main_button = tk.Button(
                card,
                text=display_text,
                font=self._font(9, "bold", "class_cards"),
                justify="center",
                wraplength=135,
                bg=label_bg,
                fg=self.theme["text"],
                activebackground=label_bg,
                activeforeground=self.theme["text"],
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda e=entry: self.open_top_editor(day_name, e),
                padx=4,
                pady=4
            )

            main_button.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0, relheight=1.0)

    def get_term_week_text(self, target_date: date) -> str:
        result = self.get_term_week_for_date(target_date)
        if not result or result == (None, None, None):
            return "School Holiday"

        _year, term_name, week_name = result
        return f"{term_name} {week_name}"

    def go_prev_week(self) -> None:
        self.view_date -= timedelta(days=7)
        self.refresh_all()

    def go_next_week(self) -> None:
        self.view_date += timedelta(days=7)
        self.refresh_all()

    def _schedule_tick(self, delay_ms: int = 30_000) -> None:
        job = getattr(self, "_tick_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
        self._tick_job = self.after(delay_ms, self.tick)

    def tick(self) -> None:
        self._tick_job = None
        # Stop once the planner has been torn down (e.g. after logging out).
        if not (hasattr(self, "days_frame") and self.days_frame.winfo_exists()):
            return
        self._schedule_tick()

        now = datetime.now()
        new_today = now.date()
        if new_today != self.today:
            self.today = new_today
            self.view_date = new_today
            self.data["app_state"]["last_seen_date"] = new_today.isoformat()
            ensure_week_records(self.data, get_week_key(new_today))
            save_data(self.data)
            self.refresh_all()

        if getattr(self, "current_overlay", None) is not None:
            return

        if should_show_friday_prompt(now, self.data["app_state"]):
            next_week_date = now.date() + timedelta(days=7)
            next_week_key = get_week_key(next_week_date)
            self.topic_prompt_queue = get_missing_topics_for_week(self.data, next_week_key)
            self.topic_prompt_index = 0
            if self.topic_prompt_queue:
                self.data["app_state"]["last_topic_prompt_date"] = now.date().isoformat()
                save_data(self.data)
                self.open_topic_prompt(next_week_key)

        if should_show_monday_prompt(now, get_week_key(now.date()), self.data):
            self.topic_prompt_queue = get_missing_topics_for_week(self.data, get_week_key(now.date()))
            self.topic_prompt_index = 0
            if self.topic_prompt_queue:
                self.data["app_state"]["last_monday_prompt_date"] = now.date().isoformat()
                save_data(self.data)
                self.open_topic_prompt(get_week_key(now.date()))

    def is_pd_day(self, target_date: date) -> bool:
        return len(self.get_pd_entries_for_date(target_date)) > 0

