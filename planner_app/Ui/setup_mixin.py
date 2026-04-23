from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import colorchooser, messagebox, ttk
from typing import Any
import json
from pathlib import Path

from planner_app.Ui.base_app import BaseApp
from planner_app.terms import HARDCODED_TERMS
from planner_app.reminders import parse_date
from planner_app.storage import make_blank_timetable, save_data
from planner_app.timetable import DAYS, PERIOD_TIMES


class SetupMixin(BaseApp):

    def show_first_run_setup(self) -> None:
        current_year = str(date.today().year)
        valid_years = [str(y) for y in range(2026, 2031)]

        self.setup_state = {
            "step": 0,
            "year": current_year if current_year in valid_years else valid_years[0],
            "master_classes": self._build_initial_master_classes(),
            "timetable": self._build_blank_setup_timetable_ids(),
        }

        self._clear_window()
        self._setup_modern_styles()
        self._build_setup_screen()

    def _clear_window(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _normalise_class_key(self, label: str) -> str:
        return " ".join(label.strip().split()).casefold()

    def _is_valid_hex_colour(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        value = value.strip()
        if len(value) != 7 or not value.startswith("#"):
            return False
        try:
            int(value[1:], 16)
            return True
        except ValueError:
            return False

    def _setup_pastel_palette(self) -> list[str]:
        return [
            "#f4b6c2", "#f7c8a2", "#f9e2ae", "#d7e8ba", "#bfe3c0",
            "#b8e0d2", "#b7dff5", "#c9d4f5", "#d7c6f3", "#ebc7e8",
            "#f6c1d0", "#ffd6bf", "#ffe7b8", "#dcedc8", "#c8ead3",
            "#c7ecee", "#cfe8ff", "#d8dcff", "#e3d5ff", "#f3d1f4",
            "#f8d5dc", "#fde2c5", "#fff1c9", "#e4f0d0", "#d5f0dc",
            "#d8f3f0", "#d9ecff", "#e2e8ff", "#ece1ff", "#f7ddf3",
        ]

    def _get_default_setup_class_colour(self, index: int) -> str:
        palette = self._setup_pastel_palette()
        return palette[index % len(palette)]

    def _build_initial_master_classes(self) -> list[dict[str, Any]]:
        classes: list[dict[str, Any]] = []
        for i in range(5):
            classes.append({
                "id": self._new_master_class_id(i + 1),
                "name": "",
                "type": "class",
                "students": "0",
                "colour": self._get_default_setup_class_colour(i),
            })
        return classes

    def _new_master_class_id(self, number: int) -> str:
        return f"setup_class_{number}"

    def _next_master_class_id(self) -> str:
        existing = self.setup_state.get("master_classes", [])
        return self._new_master_class_id(len(existing) + 1)

    def _build_blank_setup_timetable_ids(self) -> dict[str, list[dict[str, Any]]]:
        timetable: dict[str, list[dict[str, Any]]] = {}
        for day in DAYS:
            timetable[day] = []
            for period in range(1, 6):
                timetable[day].append({
                    "period": period,
                    "class_id": "",
                })
        return timetable

    def _get_master_classes_clean(self) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []

        seen_names: set[str] = set()

        for item in self.setup_state.get("master_classes", []):
            name = str(item.get("name", "")).strip()
            if not name:
                continue

            name_key = self._normalise_class_key(name)
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            item_type = str(item.get("type", "class")).strip() or "class"
            if item_type not in {"class", "label"}:
                item_type = "class"

            students_raw = str(item.get("students", "0")).strip()
            if not students_raw.isdigit():
                students_raw = "0"

            colour = str(item.get("colour", "")).strip()
            if not self._is_valid_hex_colour(colour):
                colour = self._get_default_setup_class_colour(len(cleaned))

            cleaned.append({
                "id": item.get("id") or self._next_master_class_id(),
                "name": name,
                "type": item_type,
                "students": int(students_raw),
                "colour": colour,
            })

        cleaned.sort(key=lambda x: x["name"].casefold())
        return cleaned

    def _get_master_class_name_map(self) -> dict[str, dict[str, Any]]:
        return {
            item["id"]: item
            for item in self._get_master_classes_clean()
        }

    def _get_master_class_display_names(self) -> list[str]:
        return [item["name"] for item in self._get_master_classes_clean()]

    def _get_master_class_name_to_id(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for item in self._get_master_classes_clean():
            mapping[item["name"]] = item["id"]
        return mapping

    def _get_master_class_by_id(self, class_id: str) -> dict[str, Any] | None:
        for item in self._get_master_classes_clean():
            if item["id"] == class_id:
                return item
        return None

    def _dott_entry(self, period: int) -> dict[str, Any]:
        return {
            "period": period,
            "class_id": "",
            "label": "DOTT",
            "type": "label",
            "students": 0,
        }

    # -----------------------------
    # Modern style helpers
    # -----------------------------
    def _setup_modern_styles(self) -> None:
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        panel = self.theme["panel"]
        accent = self.theme["accent"]
        text = self.theme["text"]
        outline = self.theme["outline"]

        style.configure(
            "Setup.TCombobox",
            fieldbackground=panel,
            background=panel,
            foreground=text,
            borderwidth=0,
            arrowsize=14,
            padding=6,
        )

        style.map(
            "Setup.TCombobox",
            fieldbackground=[("readonly", panel)],
            background=[("readonly", panel)],
            foreground=[("readonly", text)],
        )

        style.configure(
            "SetupSecondary.TButton",
            background=outline,
            foreground=text,
            borderwidth=0,
            focusthickness=0,
            padding=(16, 10),
            font=self._font(10, "bold", "popup_text"),
        )

        style.map(
            "SetupSecondary.TButton",
            background=[
                ("active", outline),
                ("pressed", outline),
            ],
            foreground=[("active", text)],
        )

        style.configure(
            "SetupPrimary.TButton",
            background=accent,
            foreground="white",
            borderwidth=0,
            focusthickness=0,
            padding=(18, 10),
            font=self._font(10, "bold", "popup_text"),
        )

        style.map(
            "SetupPrimary.TButton",
            background=[
                ("active", accent),
                ("pressed", accent),
            ],
            foreground=[("active", "white")],
        )

        style.configure("Setup.TFrame", background=panel)
        style.configure("Setup.TLabel", background=panel, foreground=text)

    def _make_shadow_card(self, parent: tk.Widget, width: int = 920, height: int = 660) -> tk.Frame:
        shadow = tk.Frame(parent, bg="#dccfd4")
        shadow.place(relx=0.5, rely=0.5, anchor="center", width=width + 10, height=height + 10)

        card = tk.Frame(parent, bg=self.theme["panel"], bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=width, height=height)
        return card

    def _section_label(self, parent: tk.Widget, text: str) -> tk.Label:
        lbl = tk.Label(
            parent,
            text=text,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text"),
            anchor="w"
        )
        return lbl

    def _make_underlined_entry(
        self,
        parent: tk.Widget,
        textvariable: tk.StringVar,
        width: int = 18,
    ) -> tk.Frame:
        wrap = tk.Frame(parent, bg=self.theme["panel"])
        entry = tk.Entry(
            wrap,
            textvariable=textvariable,
            font=self._font(11, "normal", "popup_text"),
            bg=self.theme["panel"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground=self.theme["text"],
            width=width,
        )
        entry.pack(fill="x", padx=0, pady=(0, 3))

        underline = tk.Frame(wrap, bg=self.theme["outline"], height=2)
        underline.pack(fill="x")

        wrap.entry = entry  # type: ignore[attr-defined]
        return wrap

    def _make_pill_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        primary: bool = False,
    ):
        style_name = "SetupPrimary.TButton" if primary else "SetupSecondary.TButton"
        return ttk.Button(parent, text=text, command=command, style=style_name)

    def _make_date_dropdowns(self, parent: tk.Widget, current_value: str = "") -> dict[str, Any]:
        months = [f"{m:02d}" for m in range(1, 13)]
        days = [f"{d:02d}" for d in range(1, 32)]

        month_val = ""
        day_val = ""

        if current_value:
            parts = current_value.split("-")
            if len(parts) == 3:
                _, month_val, day_val = parts
            elif len(parts) == 2:
                month_val, day_val = parts

        row = tk.Frame(parent, bg=self.theme["panel"])

        day_var = tk.StringVar(value=day_val if day_val in days else days[0])
        month_var = tk.StringVar(value=month_val if month_val in months else months[0])

        day_box = ttk.Combobox(
            row,
            textvariable=day_var,
            values=days,
            width=4,
            state="readonly",
            style="Setup.TCombobox"
        )
        month_box = ttk.Combobox(
            row,
            textvariable=month_var,
            values=months,
            width=4,
            state="readonly",
            style="Setup.TCombobox"
        )

        day_box.pack(side="left")
        tk.Label(
            row,
            text="-",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text"),
        ).pack(side="left", padx=4)
        month_box.pack(side="left")

        return {"frame": row, "day": day_var, "month": month_var}

    def _make_searchable_setup_combobox(
            self,
            parent: tk.Widget,
            textvariable: tk.StringVar,
            values: list[str],
            width: int = 26,
    ) -> ttk.Combobox:
        all_values = list(values)

        box = ttk.Combobox(
            parent,
            textvariable=textvariable,
            values=all_values,
            width=width,
            state="normal",
            style="Setup.TCombobox",
        )

        def _filter_values(event=None):
            typed = textvariable.get().strip().casefold()

            if not typed:
                box["values"] = all_values
                return

            filtered = [v for v in all_values if typed in v.casefold()]
            box["values"] = filtered
            box.after_idle(lambda: box.icursor(tk.END))

        def _on_selected(event=None):
            box.selection_clear()
            parent.focus_set()

        box.bind("<KeyRelease>", _filter_values)
        box.bind("<<ComboboxSelected>>", _on_selected)

        return box

    def _load_school_names(self) -> list[str]:
        try:
            file_path = Path(__file__).resolve().parent.parent / "schools.json"
            print("Looking for schools file at:", file_path)

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            names = []

            for item in data:
                school_name = str(item.get("name", "")).strip()
                if school_name:
                    names.append(school_name)

            print("Loaded schools:", len(names))
            return sorted(names)

        except Exception as e:
            print(f"Could not load schools: {e}")
            return []
    def _get_setup_step_title(self) -> tuple[str, str]:
        step = self.setup_state["step"]

        if step == 0:
            return "Welcome", "Let’s get your planner ready for first use."
        if step == 1:
            return "Classes", "Add your classes once, then use them across each day."
        day_start = 2
        day_end = day_start + len(DAYS) - 1
        if day_start <= step <= day_end:
            day_name = DAYS[step - day_start]
            return f"{day_name} Timetable", "Choose the class for each period."

        return "Setup Complete", "Everything is ready to go."

    def _get_step_progress_text(self) -> str:
        step = self.setup_state["step"]
        total = len(DAYS) + 3
        return f"Step {step + 1} of {total}"

    # -----------------------------
    # Main setup screen
    # -----------------------------
    def _build_setup_screen(self) -> None:
        self._clear_window()

        outer = tk.Frame(self, bg=self.theme["bg"])
        outer.pack(fill="both", expand=True)

        card = self._make_shadow_card(outer, width=940, height=680)

        container = tk.Frame(card, bg=self.theme["panel"], padx=42, pady=34)
        container.pack(fill="both", expand=True)

        top = tk.Frame(container, bg=self.theme["panel"])
        top.pack(fill="x", pady=(0, 18))

        self.setup_progress = tk.Label(
            top,
            text=self._get_step_progress_text(),
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(10, "bold", "popup_text"),
            anchor="w"
        )
        self.setup_progress.pack(fill="x", pady=(0, 6))

        title, subtitle = self._get_setup_step_title()

        self.setup_title = tk.Label(
            top,
            text=title,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(24, "bold", "term_title"),
            anchor="w"
        )
        self.setup_title.pack(fill="x")

        self.setup_subtitle = tk.Label(
            top,
            text=subtitle,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(11, "normal", "popup_text"),
            anchor="w",
            justify="left"
        )
        self.setup_subtitle.pack(fill="x", pady=(8, 0))

        divider = tk.Frame(container, bg=self.theme["outline"], height=1)
        divider.pack(fill="x", pady=(0, 18))

        self.setup_body = tk.Frame(container, bg=self.theme["panel"])
        self.setup_body.pack(fill="both", expand=True)

        self.setup_nav = tk.Frame(container, bg=self.theme["panel"])
        self.setup_nav.pack(fill="x", pady=(20, 0))

        self._render_setup_step()

    def _render_setup_step(self) -> None:
        for child in self.setup_body.winfo_children():
            child.destroy()
        for child in self.setup_nav.winfo_children():
            child.destroy()

        self.setup_progress.config(text=self._get_step_progress_text())
        title, subtitle = self._get_setup_step_title()
        self.setup_title.config(text=title)
        self.setup_subtitle.config(text=subtitle)

        step = self.setup_state["step"]

        if step == 0:
            self._render_setup_welcome()
        elif step == 1:
            self._render_setup_master_classes()
        elif 2 <= step <= len(DAYS) + 1:
            self._render_setup_day(DAYS[step - 2])
        else:
            self._render_setup_finish()

    # -----------------------------
    # Step 0 - Welcome
    # -----------------------------
    def _render_setup_welcome(self) -> None:
        body = self.setup_body

        self._section_label(body, "School year").pack(anchor="w", pady=(0, 8))

        self.setup_year_var = tk.StringVar(value=self.setup_state["year"])

        years = [str(y) for y in range(2026, 2031)]

        year_box = ttk.Combobox(
            body,
            textvariable=self.setup_year_var,
            values=years,
            state="readonly",
            width=10,
            style="Setup.TCombobox"
        )
        year_box.pack(anchor="w")

        self.setup_school_var = tk.StringVar()
        school_values = self._load_school_names()

        self._section_label(body, "School").pack(anchor="w", pady=(20, 8))

        school_box = self._make_searchable_setup_combobox(
            body,
            self.setup_school_var,
            school_values,
            width=45,
        )
        school_box.pack(anchor="w")

        left_nav = tk.Frame(self.setup_nav, bg=self.theme["panel"])
        left_nav.pack(side="left")

        self._make_pill_button(
            left_nav,
            "Skip for now",
            self.skip_first_run_setup,
            primary=False
        ).pack(side="left")

        self._make_pill_button(
            self.setup_nav,
            "Next",
            self._go_setup_next,
            primary=True
        ).pack(side="right")
    # -----------------------------
    # Step 1 - Master classes
    # -----------------------------
    def _render_setup_master_classes(self) -> None:
        body = self.setup_body
        self.master_class_row_vars: list[dict[str, Any]] = []

        info = tk.Label(
            body,
            text="",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(11, "normal", "popup_text"),
            justify="left",
            anchor="w"
        )
        info.pack(anchor="w", pady=(4, 16))

        outer = tk.Frame(body, bg=self.theme["panel"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=self.theme["panel"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.theme["panel"])

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _resize_scroll_frame(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        canvas.bind("<Configure>", _resize_scroll_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        header = tk.Frame(scroll_frame, bg=self.theme["panel"])
        header.pack(fill="x", pady=(0, 10))

        cols = [
            ("Class Name", 26),
            ("Type", 12),
            ("Students", 12),
            ("Colour", 14),
        ]

        for text, width in cols:
            tk.Label(
                header,
                text=text,
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "bold", "popup_text"),
                width=width,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

        for index, item in enumerate(self.setup_state["master_classes"]):
            self._render_master_class_row(scroll_frame, index, item)

        add_wrap = tk.Frame(scroll_frame, bg=self.theme["panel"])
        add_wrap.pack(fill="x", pady=(10, 4))

        self._make_pill_button(
            add_wrap,
            "Add class",
            self._add_setup_master_class_row,
            primary=False
        ).pack(side="left")

        left_nav = tk.Frame(self.setup_nav, bg=self.theme["panel"])
        left_nav.pack(side="left")

        self._make_pill_button(left_nav, "Back", self._go_setup_back, primary=False).pack(side="left")
        self._make_pill_button(left_nav, "Skip for now", self.skip_first_run_setup, primary=False).pack(side="left", padx=(10, 0))
        self._make_pill_button(self.setup_nav, "Next", self._go_setup_next, primary=True).pack(side="right")

    def _render_master_class_row(self, parent: tk.Widget, index: int, item: dict[str, Any]) -> None:
        row = tk.Frame(parent, bg=self.theme["panel"])
        row.pack(fill="x", pady=8)

        name_var = tk.StringVar(value=str(item.get("name", "")))
        type_var = tk.StringVar(value=str(item.get("type", "class")))
        students_var = tk.StringVar(value=str(item.get("students", "0")))
        colour_var = tk.StringVar(value=str(item.get("colour", self._get_default_setup_class_colour(index))))

        name_wrap = self._make_underlined_entry(row, name_var, width=24)
        name_wrap.pack(side="left", padx=(0, 10))

        type_box = ttk.Combobox(
            row,
            textvariable=type_var,
            values=["class", "label"],
            state="readonly",
            width=10,
            style="Setup.TCombobox"
        )
        type_box.pack(side="left", padx=(0, 10))

        students_wrap = self._make_underlined_entry(row, students_var, width=10)
        students_wrap.pack(side="left", padx=(0, 10))

        colour_preview = tk.Label(
            row,
            text="      ",
            bg=colour_var.get(),
            relief="solid",
            bd=1
        )
        colour_preview.pack(side="left", padx=(0, 8))

        def pick_colour() -> None:
            chosen = colorchooser.askcolor(
                title=f"Choose colour for {name_var.get().strip() or 'class'}"
            )[1]
            if not chosen:
                return
            colour_var.set(chosen)
            colour_preview.configure(bg=chosen)

        tk.Button(
            row,
            text="Pick",
            command=pick_colour,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            font=self._font(9, "bold", "popup_text"),
            padx=10,
            pady=5
        ).pack(side="left")

        self.master_class_row_vars.append({
            "id": item.get("id"),
            "name": name_var,
            "type": type_var,
            "students": students_var,
            "colour": colour_var,
        })

    def _add_setup_master_class_row(self) -> None:
        self._save_current_setup_step(validate=False)
        self.setup_state["master_classes"].append({
            "id": self._next_master_class_id(),
            "name": "",
            "type": "class",
            "students": "0",
            "colour": self._get_default_setup_class_colour(len(self.setup_state["master_classes"])),
        })
        self._render_setup_step()

    # -----------------------------
    # Day steps
    # -----------------------------
    def _render_setup_day(self, day_name: str) -> None:
        body = self.setup_body
        self.day_setup_vars: dict[int, dict[str, Any]] = {}

        tk.Label(
            body,
            text=day_name,
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text"),
            anchor="w"
        ).pack(anchor="w", pady=(0, 16))

        header = tk.Frame(body, bg=self.theme["panel"])
        header.pack(fill="x", pady=(0, 10))

        cols = [
            ("Period", 10),
            ("Time", 14),
            ("Class", 28),
        ]

        for text, width in cols:
            tk.Label(
                header,
                text=text,
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "bold", "popup_text"),
                width=width,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

        class_values = self._get_master_class_display_names()

        for period in range(1, 6):
            lesson = self.setup_state["timetable"][day_name][period - 1]
            saved_class_id = lesson.get("class_id", "")
            saved_class = self._get_master_class_by_id(saved_class_id)
            current_name = saved_class["name"] if saved_class else ""

            class_name_var = tk.StringVar(value=current_name)

            row = tk.Frame(body, bg=self.theme["panel"])
            row.pack(fill="x", pady=10)

            tk.Label(
                row,
                text=f"P{period}",
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "bold", "popup_text"),
                width=10,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

            tk.Label(
                row,
                text=PERIOD_TIMES[period],
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "normal", "popup_text"),
                width=14,
                anchor="w"
            ).pack(side="left", padx=(0, 10))

            class_box = self._make_searchable_setup_combobox(
                row,
                class_name_var,
                class_values,
                width=26,
            )
            class_box.pack(side="left", padx=(0, 10))

            self.day_setup_vars[period] = {
                "class_name": class_name_var,
                "box": class_box,
            }

        left_nav = tk.Frame(self.setup_nav, bg=self.theme["panel"])
        left_nav.pack(side="left")

        self._make_pill_button(left_nav, "Back", self._go_setup_back, primary=False).pack(side="left")
        self._make_pill_button(left_nav, "Skip for now", self.skip_first_run_setup, primary=False).pack(side="left", padx=(10, 0))

        button_text = "Finish" if day_name == DAYS[-1] else "Next"
        self._make_pill_button(
            self.setup_nav,
            button_text,
            self._go_setup_next,
            primary=True
        ).pack(side="right")

    # -----------------------------
    # Finish
    # -----------------------------
    def _render_setup_finish(self) -> None:
        wrap = tk.Frame(self.setup_body, bg=self.theme["panel"])
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap,
            text="Your planner is ready",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(18, "bold", "popup_text"),
            anchor="w"
        ).pack(anchor="w", pady=(26, 10))

        tk.Label(
            wrap,
            text=(
                "Enjoy your new planner\n"
                "Your info has been saved \n"
                "You can still edit them later in Settings."
            ),
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(12, "normal", "popup_text"),
            justify="left",
            anchor="w"
        ).pack(anchor="w")

        left_nav = tk.Frame(self.setup_nav, bg=self.theme["panel"])
        left_nav.pack(side="left")

        self._make_pill_button(left_nav, "Back", self._go_setup_back, primary=False).pack(side="left")
        self._make_pill_button(self.setup_nav, "Open planner", self.complete_first_run_setup, primary=True).pack(side="right")

    # -----------------------------
    # Navigation
    # -----------------------------
    def _go_setup_back(self) -> None:
        self._save_current_setup_step()
        self.setup_state["step"] = max(0, self.setup_state["step"] - 1)
        self._render_setup_step()

    def _go_setup_next(self) -> None:
        if not self._save_current_setup_step(validate=True):
            return

        self.setup_state["step"] += 1

        if self.setup_state["step"] > len(DAYS) + 2:
            self.setup_state["step"] = len(DAYS) + 2

        if self.setup_state["step"] == len(DAYS) + 2:
            self._save_setup_into_data()

        self._render_setup_step()

    # -----------------------------
    # Save + validate
    # -----------------------------
    def _save_current_setup_step(self, validate: bool = False) -> bool:
        step = self.setup_state["step"]

        if step == 0:
            year = self.setup_year_var.get().strip()
            if validate and (not year or not year.isdigit()):
                messagebox.showerror("Invalid year", "Please enter a valid year.")
                return False
            self.setup_state["year"] = year
            return True

        if step == 1:
            updated_rows: list[dict[str, Any]] = []

            for i, row in enumerate(getattr(self, "master_class_row_vars", [])):
                name = row["name"].get().strip()
                item_type = row["type"].get().strip() or "class"
                students = row["students"].get().strip() or "0"
                colour = row["colour"].get().strip()

                if not colour or not self._is_valid_hex_colour(colour):
                    colour = self._get_default_setup_class_colour(i)

                if validate and students and not students.isdigit():
                    messagebox.showerror("Invalid students", "Student count must be a whole number.")
                    return False

                updated_rows.append({
                    "id": row["id"],
                    "name": name,
                    "type": item_type if item_type in {"class", "label"} else "class",
                    "students": students if students.isdigit() else "0",
                    "colour": colour,
                })

            if validate:
                names_seen: set[str] = set()
                for item in updated_rows:
                    name = item["name"].strip()
                    if not name:
                        continue
                    key = self._normalise_class_key(name)
                    if key in names_seen:
                        messagebox.showerror("Duplicate class", f'"{name}" is listed more than once.')
                        return False
                    names_seen.add(key)

                if not any(item["name"].strip() for item in updated_rows):
                    messagebox.showerror("No classes", "Please add at least one class before continuing.")
                    return False

            self.setup_state["master_classes"] = updated_rows
            self._repair_setup_timetable_ids()
            return True

        if 2 <= step <= len(DAYS) + 1:
            day_name = DAYS[step - 2]
            name_to_id = self._get_master_class_name_to_id()

            for period in range(1, 6):
                typed_name = self.day_setup_vars[period]["class_name"].get().strip()
                class_id = name_to_id.get(typed_name, "")

                if validate and typed_name and not class_id:
                    messagebox.showerror(
                        "Invalid class",
                        f'"{typed_name}" is not in your Master Classes list.'
                    )
                    return False

                selected = self._get_master_class_by_id(class_id) if class_id else None

                if selected:
                    self.setup_state["timetable"][day_name][period - 1] = {
                        "period": period,
                        "class_id": selected["id"],
                        "label": selected["name"],
                        "type": selected["type"],
                        "students": selected["students"],
                    }
                else:
                    self.setup_state["timetable"][day_name][period - 1] = self._dott_entry(period)

            return True

        return True

    def _repair_setup_timetable_ids(self) -> None:
        valid_ids = {item["id"] for item in self._get_master_classes_clean()}

        for day in DAYS:
            repaired_day: list[dict[str, Any]] = []
            current_day = self.setup_state["timetable"].get(day, [])

            for period in range(1, 6):
                entry = current_day[period - 1] if period - 1 < len(current_day) else {"period": period, "class_id": ""}
                class_id = entry.get("class_id", "")

                if class_id not in valid_ids:
                    repaired_day.append(self._dott_entry(period))
                    continue

                selected = self._get_master_class_by_id(class_id)
                if selected is None:
                    repaired_day.append(self._dott_entry(period))
                    continue

                repaired_day.append({
                    "period": period,
                    "class_id": selected["id"],
                    "label": selected["name"],
                    "type": selected["type"],
                    "students": selected["students"],
                })

            self.setup_state["timetable"][day] = repaired_day

    def _save_setup_into_data(self) -> None:
        year = self.setup_state["year"].strip()
        if not year:
            return

        master_classes = self._get_master_classes_clean()
        self.data["master_classes"] = master_classes

        class_colours = self.data["settings"].setdefault("class_colours", {})
        class_colours.clear()
        for item in master_classes:
            class_colours[item["name"]] = item["colour"]

        repaired_timetable: dict[str, list[dict[str, Any]]] = {}
        valid_ids = {item["id"] for item in master_classes}

        for day in DAYS:
            repaired_timetable[day] = []
            for period in range(1, 6):
                entry = self.setup_state["timetable"][day][period - 1]
                class_id = entry.get("class_id", "")

                if class_id not in valid_ids:
                    repaired_timetable[day].append(self._dott_entry(period))
                    continue

                selected = self._get_master_class_by_id(class_id)
                if selected is None:
                    repaired_timetable[day].append(self._dott_entry(period))
                    continue

                repaired_timetable[day].append({
                    "period": period,
                    "class_id": selected["id"],
                    "label": selected["name"],
                    "type": selected["type"],
                    "students": selected["students"],
                })

        self.data["timetable"] = repaired_timetable

        self.data.setdefault("setup", {})
        self.data["setup"]["selected_year"] = year
        save_data(self.data)

    def skip_first_run_setup(self) -> None:
        self.data.setdefault("setup", {})
        self.data["setup"]["completed"] = True
        self.data["setup"]["skipped"] = True
        save_data(self.data)
        self.start_main_planner()

    def complete_first_run_setup(self) -> None:
        self._save_setup_into_data()
        self.data.setdefault("setup", {})
        self.data["setup"]["completed"] = True
        self.data["setup"]["skipped"] = False
        save_data(self.data)
        self.start_main_planner()