from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import colorchooser, messagebox, ttk
from typing import Dict
from copy import deepcopy

from planner_app.settings import PRESET_THEMES, font_folder_path, get_theme
from planner_app.storage import save_data, get_current_user, update_current_user_password
from planner_app.timetable import DAYS, TIMETABLE
from planner_app.Ui.popups_mixin import *
from planner_app.Ui.base_app import BaseApp


class SettingsMixin(BaseApp):
    def open_settings_popup(self) -> None:
        overlay = self.open_overlay()

        container = tk.Frame(
            overlay,
            bg=self.theme["panel"],
            highlightbackground=self.theme["accent"],
            highlightthickness=3
        )
        container.place(relx=0, rely=0, relwidth=1, relheight=1)

        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(
            container,
            bg=self.theme["bg"],
            width=260,
            padx=14,
            pady=14
        )
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        content_wrap = tk.Frame(container, bg=self.theme["panel"])
        content_wrap.grid(row=0, column=1, sticky="nsew")
        content_wrap.grid_rowconfigure(1, weight=1)
        content_wrap.grid_columnconfigure(0, weight=1)

        header = tk.Frame(content_wrap, bg=self.theme["panel"], padx=18, pady=14)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_label = tk.Label(
            header,
            text="Settings",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(18, "bold", "popup_text")
        )
        title_label.grid(row=0, column=0, sticky="w")

        tk.Button(
            header,
            text="Close",
            command=self.close_overlay,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            activebackground=self.theme["outline"],
            activeforeground=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=14,
            pady=8
        ).grid(row=0, column=1, sticky="e")

        page_host = tk.Frame(content_wrap, bg=self.theme["panel"])
        page_host.grid(row=1, column=0, sticky="nsew")
        page_host.grid_rowconfigure(0, weight=1)
        page_host.grid_columnconfigure(0, weight=1)

        pages: dict[str, tk.Frame] = {}
        nav_buttons: dict[str, tk.Button] = {}

        def make_page(name: str):
            outer, inner = self.make_scrollable(page_host)
            outer.grid(row=0, column=0, sticky="nsew")
            pages[name] = outer
            return inner

        planner_tab = make_page("Planner")
        pd_tab = make_page("PD Days")
        relief_tab = make_page("Relief")
        general_tab = make_page("General")
        custom_tab = make_page("Customisation")

        self._build_planner_settings(planner_tab)
        self._build_pd_days_settings(pd_tab)
        self._build_relief_settings(relief_tab)
        self._build_general_settings(general_tab)
        self._build_customisation_settings(custom_tab)

        def show_page(name: str) -> None:
            for frame in pages.values():
                frame.grid_remove()

            for btn_name, btn in nav_buttons.items():
                if btn_name == name:
                    btn.configure(bg=self.theme["accent"], fg="white")
                else:
                    btn.configure(bg=self.theme["outline"], fg=self.theme["text"])

            title_label.configure(text=name)
            pages[name].grid()

        def add_nav_button(name: str) -> None:
            btn = tk.Button(
                sidebar,
                text=name,
                command=lambda n=name: show_page(n),
                anchor="w",
                bg=self.theme["outline"],
                fg=self.theme["text"],
                activebackground=self.theme["accent"],
                activeforeground="white",
                relief="flat",
                bd=0,
                cursor="hand2",
                font=self._font(11, "bold", "popup_text"),
                padx=14,
                pady=12
            )
            btn.pack(fill="x", pady=(0, 8))
            nav_buttons[name] = btn

        tk.Label(
            sidebar,
            text="Settings",
            bg=self.theme["bg"],
            fg=self.theme["accent"],
            font=self._font(16, "bold", "popup_text")
        ).pack(anchor="w", pady=(0, 16))

        add_nav_button("Planner")
        add_nav_button("PD Days")
        add_nav_button("Relief")
        add_nav_button("General")
        add_nav_button("Customisation")

        show_page("Planner")

    def _make_section_card(self, parent: tk.Widget, title: str, description: str = "") -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=self.theme["panel"],
            highlightbackground=self.theme["outline"],
            highlightthickness=1,
            padx=12,
            pady=12
        )
        card.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(
            card,
            text=title,
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(12, "bold", "popup_text")
        ).pack(anchor="w")

        if description:
            tk.Label(
                card,
                text=description,
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "normal", "popup_text")
            ).pack(anchor="w", pady=(4, 10))

        body = tk.Frame(card, bg=self.theme["panel"])
        body.pack(fill="both", expand=True)
        return body

    def _build_planner_settings(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Planner Settings",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            parent,
            text="Manage timetable adjustments, assessments, and lesson topics in one place.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w", padx=12, pady=(0, 14))

        timetable_body = self._make_section_card(
            parent,
            "Timetable Adjustments",
            "Edit class names, types, student numbers, and colours."
        )
        self._build_timetable_settings(timetable_body)

        assignment_body = self._make_section_card(
            parent,
            "Assessments",
            "Add, edit, and remove assessments."
        )
        self._build_assignment_setting(assignment_body)

        topic_body = self._make_section_card(
            parent,
            "Lesson Topics",
            "Manage weekly lesson topics by class."
        )
        self._build_topic_over_setting(topic_body)

    def _build_general_settings(self, parent: tk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        current_user = get_current_user(self.data)

        account_frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            highlightbackground=self.theme["outline"],
            highlightthickness=1,
            padx=12,
            pady=12
        )
        account_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 12))
        account_frame.columnconfigure(0, weight=1)

        tk.Label(
            account_frame,
            text="Account",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(12, "bold", "popup_text")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        if current_user:
            tk.Label(
                account_frame,
                text=f"Username: {current_user.get('username', '')}",
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "normal", "popup_text")
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

            tk.Label(
                account_frame,
                text=f"Email: {current_user.get('email', '')}",
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "normal", "popup_text")
            ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))
        else:
            tk.Label(
                account_frame,
                text="No user is currently signed in.",
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "normal", "popup_text")
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        tk.Label(
            account_frame,
            text="Current password",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text")
        ).grid(row=3, column=0, sticky="w", pady=(6, 4))

        current_password_var = tk.StringVar()
        tk.Entry(
            account_frame,
            textvariable=current_password_var,
            show="*",
            font=self._font(10, "normal", "popup_text")
        ).grid(row=4, column=0, sticky="ew", padx=(0, 10), pady=(0, 8))

        tk.Label(
            account_frame,
            text="New password",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text")
        ).grid(row=5, column=0, sticky="w", pady=(6, 4))

        new_password_var = tk.StringVar()
        tk.Entry(
            account_frame,
            textvariable=new_password_var,
            show="*",
            font=self._font(10, "normal", "popup_text")
        ).grid(row=6, column=0, sticky="ew", padx=(0, 10), pady=(0, 8))

        tk.Label(
            account_frame,
            text="Confirm new password",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text")
        ).grid(row=7, column=0, sticky="w", pady=(6, 4))

        confirm_password_var = tk.StringVar()
        tk.Entry(
            account_frame,
            textvariable=confirm_password_var,
            show="*",
            font=self._font(10, "normal", "popup_text")
        ).grid(row=8, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))

        button_row = tk.Frame(account_frame, bg=self.theme["panel"])
        button_row.grid(row=9, column=0, sticky="w")

        def check_for_updates() -> None:
            messagebox.showinfo(
                "Update planner",
                "This button is ready for your updater logic. "
                "You can connect it to your server version check next."
            )

        def save_general() -> None:
            if not current_user:
                messagebox.showerror("No user", "No signed-in user was found.")
                return

            current_password = current_password_var.get()
            new_password = new_password_var.get()
            confirm_password = confirm_password_var.get()

            if not current_password or not new_password or not confirm_password:
                messagebox.showerror("Missing information", "Please fill in all password fields.")
                return

            if new_password != confirm_password:
                messagebox.showerror("Password mismatch", "The new passwords do not match.")
                return

            success, message = update_current_user_password(self.data, current_password, new_password)
            if not success:
                messagebox.showerror("Could not update password", message)
                return

            save_data(self.data)
            current_password_var.set("")
            new_password_var.set("")
            confirm_password_var.set("")
            messagebox.showinfo("Saved", "Your password has been updated.")

        tk.Button(
            button_row,
            text="Change password",
            command=save_general,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Update planner",
            command=check_for_updates,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Log out",
            command=self.logout_user,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).pack(side="left")

    def _build_customisation_settings(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Customisation",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            parent,
            text="Choose a preset theme and set your fonts.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w", padx=12, pady=(0, 14))

        theme_frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            highlightbackground=self.theme["outline"],
            highlightthickness=1,
            padx=12,
            pady=12
        )
        theme_frame.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(
            theme_frame,
            text="Preset Themes",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(12, "bold", "popup_text")
        ).pack(anchor="w", pady=(0, 8))

        theme_var = tk.StringVar(value=self.settings.get("current_theme", "Apricot"))

        for theme_name in PRESET_THEMES:
            tk.Radiobutton(
                theme_frame,
                text=theme_name,
                value=theme_name,
                variable=theme_var,
                bg=self.theme["panel"],
                fg=self.theme["text"],
                activebackground=self.theme["panel"],
                activeforeground=self.theme["text"],
                selectcolor=self.theme["panel"],
                font=self._font(10, "normal", "popup_text"),
                anchor="w"
            ).pack(anchor="w", pady=2)

        font_frame = tk.Frame(
            parent,
            bg=self.theme["panel"],
            highlightbackground=self.theme["outline"],
            highlightthickness=1,
            padx=12,
            pady=12
        )
        font_frame.pack(fill="x", padx=12, pady=(0, 12))

        self._build_font_settings(font_frame)

        def save_customisation() -> None:
            self.settings["current_theme"] = theme_var.get()
            save_data(self.data)
            self.settings = self.data["settings"]
            self.theme = get_theme(self.settings)
            self.close_overlay()
            self.refresh_all()

        tk.Button(
            parent,
            text="Save Customisation",
            command=save_customisation,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).pack(anchor="w", padx=12, pady=(0, 12))

    def _build_relief_settings(self, parent: tk.Frame) -> None:
        relief_days = self.data.setdefault("relief_days", [])

        tk.Label(
            parent,
            text="Relief",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            parent,
            text="Add dates where you are off and relief is covering your classes.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w", padx=12, pady=(0, 12))

        controls = tk.Frame(parent, bg=self.theme["panel"])
        controls.pack(fill="x", padx=12, pady=(0, 10))

        today = date.today()
        day_var = tk.StringVar(value=str(today.day))
        month_var = tk.StringVar(value=str(today.month))
        year_var = tk.StringVar(value=str(today.year))
        note_var = tk.StringVar()

        tk.Label(controls, text="Day", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(controls, textvariable=day_var, values=[str(i) for i in range(1, 32)],
                     state="readonly", width=6).grid(row=1, column=0, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="Month", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Combobox(controls, textvariable=month_var, values=[str(i) for i in range(1, 13)],
                     state="readonly", width=8).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="Year", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            controls,
            textvariable=year_var,
            values=[str(i) for i in range(today.year - 1, today.year + 6)],
            state="readonly",
            width=8
        ).grid(row=1, column=2, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="Note", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        tk.Entry(
            controls,
            textvariable=note_var,
            font=self._font(10, "normal", "popup_text")
        ).grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        controls.columnconfigure(3, weight=1)

        list_wrap = tk.Frame(parent, bg=self.theme["panel"])
        list_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        listbox = tk.Listbox(
            list_wrap,
            font=self._font(10, "normal", "popup_text"),
            bg="white",
            fg=self.theme["text"],
            height=12
        )
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_wrap, command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        def refresh_relief_list() -> None:
            listbox.delete(0, "end")
            relief_days.sort(key=lambda x: x.get("date", ""))
            for item in relief_days:
                listbox.insert("end", f"{item.get('date', '')} | {item.get('note', 'Relief')}")

        def add_relief_day() -> None:
            try:
                selected_date = date(
                    int(year_var.get()),
                    int(month_var.get()),
                    int(day_var.get())
                ).isoformat()
            except ValueError:
                messagebox.showerror("Invalid date", "Please choose a valid date.")
                return

            entry = {
                "date": selected_date,
                "note": note_var.get().strip() or "Relief"
            }

            if entry not in relief_days:
                relief_days.append(entry)

            save_data(self.data)
            refresh_relief_list()
            self.refresh_all()

        def remove_relief_day() -> None:
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror("No selection", "Select a relief entry to remove.")
                return

            selected_text = listbox.get(selection[0])
            new_list = []
            removed = False

            for item in relief_days:
                line = f"{item.get('date', '')} | {item.get('note', 'Relief')}"
                if not removed and line == selected_text:
                    removed = True
                    continue
                new_list.append(item)

            self.data["relief_days"] = new_list
            save_data(self.data)
            refresh_relief_list()
            self.refresh_all()

        btn_row = tk.Frame(parent, bg=self.theme["panel"])
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            btn_row,
            text="Add Relief Day",
            command=add_relief_day,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="Remove Selected",
            command=remove_relief_day,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left")

        refresh_relief_list()

    def _build_timetable_settings(self, parent: tk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        timetable_data = self.data.setdefault("timetable", deepcopy(TIMETABLE))
        self.settings.setdefault("class_colours", {})
        self.settings.setdefault("label_colours", {})

        entry_vars = {}
        colour_vars = {}
        row = 0

        for day in DAYS:
            tk.Label(
                parent,
                text=day,
                bg=self.theme["panel"],
                fg=self.theme["accent"],
                font=self._font(11, "bold", "popup_text")
            ).grid(row=row, column=0, columnspan=6, sticky="w", padx=0, pady=(10, 6))
            row += 1

            for lesson in timetable_data[day]:
                period = lesson["period"]
                label = lesson["label"]
                entry_type = lesson["type"]

                tk.Label(
                    parent,
                    text=f"P{period}",
                    bg=self.theme["panel"],
                    fg=self.theme["text"],
                    font=self._font(10, "bold", "popup_text"),
                    width=6
                ).grid(row=row, column=0, sticky="w", padx=(8, 6), pady=4)

                label_var = tk.StringVar(value=label)
                students_var = tk.StringVar(value=str(lesson.get("students", "")))
                type_var = tk.StringVar(value=entry_type)

                entry_vars[(day, period)] = {
                    "label": label_var,
                    "students": students_var,
                }

                tk.Entry(
                    parent,
                    textvariable=label_var,
                    font=self._font(10, "normal", "popup_text")
                ).grid(row=row, column=1, sticky="ew", padx=6, pady=4)

                ttk.Combobox(
                    parent,
                    textvariable=type_var,
                    values=["class", "label"],
                    state="readonly",
                    width=10
                ).grid(row=row, column=2, padx=6, pady=4, sticky="w")

                tk.Entry(
                    parent,
                    textvariable=students_var,
                    font=self._font(10, "normal", "popup_text"),
                    width=6
                ).grid(row=row, column=3, padx=6, pady=4, sticky="w")

                preview_bg = self.get_class_colour(label) if entry_type == "class" else self.get_label_colour(label)
                colour_preview = tk.Label(parent, text="      ", bg=preview_bg, relief="solid", bd=1)
                colour_preview.grid(row=row, column=4, padx=6, pady=4, sticky="w")

                colour_vars[(day, period)] = {
                    "type_var": type_var,
                    "label_var": label_var,
                    "preview": colour_preview,
                }

                def choose_colour(day_name=day, p=period):
                    current = colour_vars[(day_name, p)]
                    chosen = colorchooser.askcolor(title="Choose timetable colour")[1]
                    if not chosen:
                        return

                    item_name = current["label_var"].get().strip()
                    item_type = current["type_var"].get().strip()

                    if not item_name:
                        return

                    current["preview"].configure(bg=chosen)
                    if item_type == "class":
                        self.set_class_colour(item_name, chosen)
                    else:
                        self.set_label_colour(item_name, chosen)

                tk.Button(
                    parent,
                    text="Pick",
                    command=choose_colour,
                    bg=self.theme["outline"],
                    fg=self.theme["text"],
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    font=self._font(8, "bold", "popup_text"),
                    padx=8,
                    pady=4
                ).grid(row=row, column=5, padx=(0, 6), pady=4, sticky="w")

                row += 1

        def save_timetable_settings() -> None:
            new_timetable = {}
            old_to_new_names = {}
            label_type_map = {}

            for day_name in DAYS:
                new_timetable[day_name] = []
                for lesson in timetable_data[day_name]:
                    period = lesson["period"]
                    old_label = lesson["label"]

                    new_label = entry_vars[(day_name, period)]["label"].get().strip()
                    students_value = entry_vars[(day_name, period)]["students"].get().strip()
                    chosen_type = colour_vars[(day_name, period)]["type_var"].get().strip()

                    if not new_label:
                        messagebox.showerror("Invalid class", f"{day_name} period {period} cannot be blank.")
                        return

                    if new_label in label_type_map:
                        new_type = label_type_map[new_label]
                    else:
                        new_type = chosen_type
                        label_type_map[new_label] = new_type

                    new_timetable[day_name].append({
                        "period": period,
                        "label": new_label,
                        "type": new_type,
                        "students": int(students_value) if students_value.isdigit() else 0
                    })

                    if old_label != new_label:
                        old_to_new_names[old_label] = new_label

            self.data["timetable"] = new_timetable
            class_colours = self.settings.setdefault("class_colours", {})
            label_colours = self.settings.setdefault("label_colours", {})

            for old_name, new_name in old_to_new_names.items():
                old_label_key = old_name.strip().upper()
                new_label_key = new_name.strip().upper()

                if old_name in class_colours and new_name not in class_colours:
                    class_colours[new_name] = class_colours[old_name]

                if old_label_key in label_colours and new_label_key not in label_colours:
                    label_colours[new_label_key] = label_colours[old_label_key]

            save_data(self.data)
            self.refresh_all()
            messagebox.showinfo("Saved", "Timetable settings saved.")

        tk.Button(
            parent,
            text="Save Timetable Settings",
            command=save_timetable_settings,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).grid(row=row, column=0, columnspan=6, sticky="w", padx=0, pady=16)

    def _build_assignment_setting(self, parent: tk.Frame) -> None:
        assignments = self.data.setdefault("assignments", [])

        form = tk.Frame(parent, bg=self.theme["panel"])
        form.pack(fill="x", pady=(0, 10))

        tk.Label(form, text="Class", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        tk.Label(form, text="Title", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        tk.Label(form, text="Year", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        tk.Label(form, text="Term", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        tk.Label(form, text="Week", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=4, sticky="w", padx=4, pady=4)
        tk.Label(form, text="Lesson", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=5, sticky="w", padx=4, pady=4)

        class_names = sorted({
            lesson["label"]
            for day in self.data.get("timetable", {}).values()
            for lesson in day
            if lesson.get("type") == "class"
        })

        years = sorted(self.settings.get("terms", {}).keys()) or [str(date.today().year)]
        terms = ["Term 1", "Term 2", "Term 3", "Term 4"]
        weeks = [f"Week {i}" for i in range(1, 12)]

        def get_class_lessons(class_name: str) -> list[str]:
            periods = []
            for day in DAYS:
                for lesson in self.data.get("timetable", {}).get(day, []):
                    if lesson.get("type") == "class" and lesson.get("label") == class_name:
                        period = lesson.get("period")
                        if isinstance(period, int):
                            periods.append(period)
            periods = sorted(set(periods))
            return [f"Lesson {period}" for period in periods]

        class_var = tk.StringVar(value=class_names[0] if class_names else "")
        title_var = tk.StringVar()
        year_var = tk.StringVar(value=str(date.today().year) if str(date.today().year) in years else years[0])
        term_var = tk.StringVar(value="Term 1")
        week_var = tk.StringVar(value="Week 1")

        initial_lessons = get_class_lessons(class_var.get()) if class_names else ["Lesson 1"]
        lesson_var = tk.StringVar(value=initial_lessons[0] if initial_lessons else "")

        ttk.Combobox(form, textvariable=class_var, values=class_names, state="readonly", width=20)\
            .grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        tk.Entry(form, textvariable=title_var, font=self._font(10, "normal", "popup_text"))\
            .grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ttk.Combobox(form, textvariable=year_var, values=years, state="readonly", width=8)\
            .grid(row=1, column=2, padx=4, pady=4, sticky="ew")
        ttk.Combobox(form, textvariable=term_var, values=terms, state="readonly", width=10)\
            .grid(row=1, column=3, padx=4, pady=4, sticky="ew")
        ttk.Combobox(form, textvariable=week_var, values=weeks, state="readonly", width=10)\
            .grid(row=1, column=4, padx=4, pady=4, sticky="ew")

        lesson_combo = ttk.Combobox(form, textvariable=lesson_var, values=initial_lessons, state="readonly", width=10)
        lesson_combo.grid(row=1, column=5, padx=4, pady=4, sticky="ew")

        form.columnconfigure(1, weight=1)

        list_wrap = tk.Frame(parent, bg=self.theme["panel"])
        list_wrap.pack(fill="both", expand=True, pady=(0, 10))

        listbox = tk.Listbox(
            list_wrap,
            font=self._font(10, "normal", "popup_text"),
            bg="white",
            fg=self.theme["text"],
            height=12
        )
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_wrap, command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        selected_index = {"value": None}

        def make_assignment_id() -> str:
            existing = {a.get("id", "") for a in assignments}
            i = 1
            while f"a{i}" in existing:
                i += 1
            return f"a{i}"

        def sort_key(item):
            week_num = int(str(item.get("week", "Week 1")).replace("Week ", "") or 1)
            lesson_num = int(str(item.get("lesson", "Lesson 1")).replace("Lesson ", "") or 1)

            day_order = {
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
            }

            return (
                item.get("year", ""),
                item.get("term", ""),
                week_num,
                day_order.get(item.get("day", ""), 99),
                lesson_num,
                item.get("class", ""),
                item.get("title", ""),
            )

        def refresh_list() -> None:
            listbox.delete(0, "end")
            assignments.sort(key=sort_key)
            for item in assignments:
                listbox.insert(
                    "end",
                    f"{item.get('year', '')} | {item.get('term', '')} | {item.get('week', '')} | "
                    f"{item.get('day', '')} | {item.get('lesson', '')} | "
                    f"{item.get('class', '')} | {item.get('title', '')}"
                )
            selected_index["value"] = None

        def refresh_lesson_dropdown(*_args) -> None:
            lessons_for_class = get_class_lessons(class_var.get().strip())
            lesson_combo["values"] = lessons_for_class
            current = lesson_var.get().strip()
            if current not in lessons_for_class:
                lesson_var.set(lessons_for_class[0] if lessons_for_class else "")

        def clear_form() -> None:
            title_var.set("")
            if class_names:
                class_var.set(class_names[0])
            year_var.set(str(date.today().year) if str(date.today().year) in years else years[0])
            term_var.set("Term 1")
            week_var.set("Week 1")
            refresh_lesson_dropdown()
            selected_index["value"] = None
            listbox.selection_clear(0, "end")

        def save_assignments() -> None:
            save_data(self.data)
            self.refresh_all()

        def add_assignment() -> None:
            cls = class_var.get().strip()
            title = title_var.get().strip()
            year_value = year_var.get().strip()
            term_value = term_var.get().strip()
            week_value = week_var.get().strip()
            lesson_value = lesson_var.get().strip()

            if not cls or not title or not lesson_value:
                messagebox.showerror("Missing information", "Please fill in class, title, and lesson.")
                return

            assignments.append({
                "id": make_assignment_id(),
                "class": cls,
                "title": title,
                "year": year_value,
                "term": term_value,
                "week": week_value,
                "lesson": lesson_value,
            })
            save_assignments()
            refresh_list()
            clear_form()

        def load_selected(_event=None) -> None:
            selection = listbox.curselection()
            if not selection:
                return

            idx = selection[0]
            selected_index["value"] = idx
            item = assignments[idx]

            class_var.set(item.get("class", ""))
            title_var.set(item.get("title", ""))
            year_var.set(item.get("year", years[0]))
            term_var.set(item.get("term", "Term 1"))
            week_var.set(item.get("week", "Week 1"))

            refresh_lesson_dropdown()
            lesson_var.set(item.get("lesson", lesson_var.get()))

        def update_selected() -> None:
            idx = selected_index["value"]
            if idx is None:
                messagebox.showerror("No selection", "Select an assessment to edit.")
                return

            cls = class_var.get().strip()
            title = title_var.get().strip()
            lesson_value = lesson_var.get().strip()

            if not cls or not title or not lesson_value:
                messagebox.showerror("Missing information", "Please fill in class, title, and lesson.")
                return

            assignments[idx]["class"] = cls
            assignments[idx]["title"] = title
            assignments[idx]["year"] = year_var.get().strip()
            assignments[idx]["term"] = term_var.get().strip()
            assignments[idx]["week"] = week_var.get().strip()
            assignments[idx]["lesson"] = lesson_value

            save_assignments()
            refresh_list()
            clear_form()

        def delete_selected() -> None:
            idx = selected_index["value"]
            if idx is None:
                messagebox.showerror("No selection", "Select an assessment to delete.")
                return

            del assignments[idx]
            save_assignments()
            refresh_list()
            clear_form()

        btn_row = tk.Frame(parent, bg=self.theme["panel"])
        btn_row.pack(fill="x", pady=(0, 12))

        tk.Button(
            btn_row,
            text="Add",
            command=add_assignment,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="Update Selected",
            command=update_selected,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="Delete Selected",
            command=delete_selected,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left")

        class_var.trace_add("write", refresh_lesson_dropdown)
        listbox.bind("<<ListboxSelect>>", load_selected)

        refresh_lesson_dropdown()
        refresh_list()

    def _build_topic_over_setting(self, parent: tk.Frame) -> None:
        self.data.setdefault("topic_overview", {})

        top_controls = tk.Frame(parent, bg=self.theme["panel"])
        top_controls.pack(fill="x", pady=(0, 10))

        class_names = sorted({
            lesson["label"]
            for day in self.data.get("timetable", {}).values()
            for lesson in day
            if lesson.get("type") == "class"
        })

        years = sorted(self.settings.get("terms", {}).keys()) or [str(date.today().year)]
        terms = ["Term 1", "Term 2", "Term 3", "Term 4"]
        weeks = [f"Week {i}" for i in range(1, 12)]

        class_var = tk.StringVar(value=class_names[0] if class_names else "")
        year_var = tk.StringVar(value=str(date.today().year) if str(date.today().year) in years else years[0])
        term_var = tk.StringVar(value="Term 1")
        week_var = tk.StringVar(value="Week 1")

        tk.Label(top_controls, text="Class", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(top_controls, textvariable=class_var, values=class_names, state="readonly", width=22)\
            .grid(row=1, column=0, sticky="ew", padx=4, pady=4)

        tk.Label(top_controls, text="Year", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Combobox(top_controls, textvariable=year_var, values=years, state="readonly", width=10)\
            .grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        tk.Label(top_controls, text="Term", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(top_controls, textvariable=term_var, values=terms, state="readonly", width=10)\
            .grid(row=1, column=2, sticky="ew", padx=4, pady=4)

        tk.Label(top_controls, text="Week", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Combobox(top_controls, textvariable=week_var, values=weeks, state="readonly", width=10)\
            .grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        entries_wrap = tk.Frame(parent, bg=self.theme["panel"])
        entries_wrap.pack(fill="both", expand=True, pady=(0, 10))
        entries_wrap.columnconfigure(1, weight=1)

        day_entries = {}
        day_row_widgets = {}

        def get_class_days(class_name: str) -> list[str]:
            days_for_class = []
            for day in DAYS:
                for lesson in self.data.get("timetable", {}).get(day, []):
                    if lesson.get("type") == "class" and lesson.get("label") == class_name:
                        days_for_class.append(day)
                        break
            return days_for_class

        def rebuild_day_entries(*_args) -> None:
            for widgets in day_row_widgets.values():
                for widget in widgets:
                    widget.destroy()
            day_row_widgets.clear()
            day_entries.clear()

            selected_class = class_var.get().strip()
            class_days = get_class_days(selected_class)

            for row, day in enumerate(class_days):
                label = tk.Label(
                    entries_wrap,
                    text=day,
                    bg=self.theme["panel"],
                    fg=self.theme["accent"],
                    font=self._font(10, "bold", "popup_text"),
                    width=12,
                    anchor="w"
                )
                label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=6)

                entry = tk.Entry(entries_wrap, font=self._font(10, "normal", "popup_text"))
                entry.grid(row=row, column=1, sticky="ew", padx=4, pady=6)

                day_entries[day] = entry
                day_row_widgets[day] = (label, entry)

            load_week()

        def load_week(*_args) -> None:
            selected_class = class_var.get().strip()
            selected_year = year_var.get().strip()
            selected_term = term_var.get().strip()
            selected_week = week_var.get().strip()

            for day, entry_widget in day_entries.items():
                entry_widget.delete(0, "end")
                entry_widget.insert(
                    0,
                    self.get_topic_for_slot(
                        selected_class,
                        selected_year,
                        selected_term,
                        selected_week,
                        day
                    )
                )

        def save_week() -> None:
            selected_class = class_var.get().strip()
            selected_year = year_var.get().strip()
            selected_term = term_var.get().strip()
            selected_week = week_var.get().strip()

            if not selected_class:
                messagebox.showerror("Missing class", "Please select a class.")
                return

            for day, entry_widget in day_entries.items():
                self.set_topic_for_slot(
                    selected_class,
                    selected_year,
                    selected_term,
                    selected_week,
                    day,
                    entry_widget.get().strip()
                )

            save_data(self.data)
            self.refresh_all()
            messagebox.showinfo("Saved", "Lesson topics saved.")

        class_var.trace_add("write", rebuild_day_entries)
        year_var.trace_add("write", load_week)
        term_var.trace_add("write", load_week)
        week_var.trace_add("write", load_week)

        rebuild_day_entries()

        tk.Button(
            parent,
            text="Save Lesson Topics",
            command=save_week,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).pack(anchor="w", pady=(0, 12))

    def _build_font_settings(self, parent: tk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        font_choices = ["Segoe UI", "Arial", "Calibri", "Verdana", "Trebuchet MS", "Tahoma", "Comic Sans MS"]
        for loaded_font in self.local_fonts:
            if loaded_font not in font_choices:
                font_choices.append(loaded_font)

        font_sections = self.settings.setdefault("font_sections", {})
        section_vars = {}
        section_labels = {
            "term_title": "Term / Week title",
            "day_headers": "Day headers",
            "class_cards": "Class cards",
            "todo_title": "To-do title",
            "todo_items": "To-do items",
            "reminder_cards": "Reminder cards",
            "popup_text": "Popup text",
        }

        row = 0
        tk.Label(
            parent,
            text="Fonts",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(12, "bold", "popup_text")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=0, pady=(0, 10))
        row += 1

        for key, label_text in section_labels.items():
            tk.Label(
                parent,
                text=label_text,
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=self._font(10, "bold", "popup_text")
            ).grid(row=row, column=0, sticky="w", padx=0, pady=6)

            var = tk.StringVar(value=font_sections.get(key, self.settings.get("font_family", "Segoe UI")))
            section_vars[key] = var

            ttk.Combobox(
                parent,
                textvariable=var,
                values=font_choices,
                state="readonly",
                font=self._font(10, "normal", "popup_text")
            ).grid(row=row, column=1, sticky="ew", padx=10, pady=6)
            row += 1

        tk.Label(
            parent,
            text="Preview text",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(11, "bold", "popup_text")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=0, pady=(12, 4))
        row += 1

        preview_labels = {}
        for key, label_text in section_labels.items():
            preview = tk.Label(
                parent,
                text=f"{label_text}: ABC abc 123",
                bg=self.theme["panel"],
                fg=self.theme["text"],
                font=(section_vars[key].get(), 11, "normal"),
                anchor="w"
            )
            preview.grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=2)
            preview_labels[key] = preview
            row += 1

        def update_previews(*_):
            for key, preview in preview_labels.items():
                preview.config(font=(section_vars[key].get() or "Segoe UI", 11, "normal"))

        for var in section_vars.values():
            var.trace_add("write", update_previews)

        tk.Label(
            parent,
            text=f"Font folder: {font_folder_path()}",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(9, "normal", "popup_text")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=0, pady=(8, 12))
        row += 1

        tk.Button(
            parent,
            text="Save Font Settings",
            command=lambda: self.save_font_settings(section_vars),
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12,
            pady=8
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=0, pady=(0, 0))

    def _build_pd_days_settings(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="Personal Development Days",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            parent,
            text="Add full-day or partial-day PD sessions.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w", padx=12, pady=(0, 10))

        controls = tk.Frame(parent, bg=self.theme["panel"])
        controls.pack(fill="x", padx=12, pady=(0, 10))

        today = date.today()
        day_var = tk.StringVar(value=str(today.day))
        month_var = tk.StringVar(value=str(today.month))
        year_var = tk.StringVar(value=str(today.year))

        pd_type_var = tk.StringVar(value="Full day")
        first_count_var = tk.StringVar(value="1")

        selected_period_vars = {
            1: tk.BooleanVar(value=False),
            2: tk.BooleanVar(value=False),
            3: tk.BooleanVar(value=False),
            4: tk.BooleanVar(value=False),
            5: tk.BooleanVar(value=False),
        }

        tk.Label(controls, text="Day", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(controls, textvariable=day_var, values=[str(i) for i in range(1, 32)],
                     state="readonly", width=6).grid(row=1, column=0, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="Month", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ttk.Combobox(controls, textvariable=month_var, values=[str(i) for i in range(1, 13)],
                     state="readonly", width=8).grid(row=1, column=1, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="Year", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            controls,
            textvariable=year_var,
            values=[str(i) for i in range(today.year - 1, today.year + 6)],
            state="readonly",
            width=8
        ).grid(row=1, column=2, sticky="w", padx=4, pady=4)

        tk.Label(controls, text="PD Type", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ttk.Combobox(
            controls,
            textvariable=pd_type_var,
            values=["Full day", "First X periods", "Selected periods"],
            state="readonly",
            width=18
        ).grid(row=1, column=3, sticky="w", padx=4, pady=4)

        extra_wrap = tk.Frame(parent, bg=self.theme["panel"])
        extra_wrap.pack(fill="x", padx=12, pady=(0, 10))

        first_periods_frame = tk.Frame(extra_wrap, bg=self.theme["panel"])
        tk.Label(
            first_periods_frame,
            text="Number of periods",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text")
        ).pack(side="left", padx=(0, 8))
        ttk.Combobox(
            first_periods_frame,
            textvariable=first_count_var,
            values=[str(i) for i in range(1, 6)],
            state="readonly",
            width=6
        ).pack(side="left")

        selected_periods_frame = tk.Frame(extra_wrap, bg=self.theme["panel"])
        tk.Label(
            selected_periods_frame,
            text="Select periods",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "bold", "popup_text")
        ).pack(side="left", padx=(0, 8))

        for period in range(1, 6):
            tk.Checkbutton(
                selected_periods_frame,
                text=f"P{period}",
                variable=selected_period_vars[period],
                bg=self.theme["panel"],
                fg=self.theme["text"],
                activebackground=self.theme["panel"],
                font=self._font(10, "normal", "popup_text")
            ).pack(side="left", padx=(0, 8))

        def refresh_pd_type_controls(*_args) -> None:
            first_periods_frame.pack_forget()
            selected_periods_frame.pack_forget()

            chosen = pd_type_var.get().strip()
            if chosen == "First X periods":
                first_periods_frame.pack(anchor="w")
            elif chosen == "Selected periods":
                selected_periods_frame.pack(anchor="w")

        pd_type_var.trace_add("write", refresh_pd_type_controls)
        refresh_pd_type_controls()

        list_wrap = tk.Frame(parent, bg=self.theme["panel"])
        list_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        listbox = tk.Listbox(
            list_wrap,
            font=self._font(10, "normal", "popup_text"),
            bg="white",
            fg=self.theme["text"],
            height=12
        )
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_wrap, command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        def normalise_pd_entry(entry):
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

        def pd_sort_key(item):
            norm = normalise_pd_entry(item)
            if not norm:
                return ("9999-99-99", "z")
            return (norm.get("date", ""), norm.get("type", ""))

        def format_pd_entry(entry) -> str:
            norm = normalise_pd_entry(entry)
            if not norm:
                return "Invalid PD entry"

            date_text = norm["date"]
            entry_type = norm["type"]

            if entry_type == "full":
                return f"{date_text} | Full day"
            if entry_type == "first_periods":
                return f"{date_text} | First {norm.get('count', 0)} periods"
            if entry_type == "selected_periods":
                periods = norm.get("periods", [])
                periods_text = ", ".join(f"P{p}" for p in periods)
                return f"{date_text} | Selected periods: {periods_text}"

            return f"{date_text} | Full day"

        def refresh_pd_list() -> None:
            listbox.delete(0, "end")
            pd_days = self.data.get("pd_days", [])
            for entry in sorted(pd_days, key=pd_sort_key):
                listbox.insert("end", format_pd_entry(entry))

        def build_new_pd_entry():
            try:
                pd_date = date(
                    int(year_var.get()),
                    int(month_var.get()),
                    int(day_var.get())
                ).isoformat()
            except ValueError:
                messagebox.showerror("Invalid date", "Please choose a valid date.")
                return None

            chosen_type = pd_type_var.get().strip()

            if chosen_type == "Full day":
                return {"date": pd_date, "type": "full"}

            if chosen_type == "First X periods":
                count = int(first_count_var.get())
                return {"date": pd_date, "type": "first_periods", "count": count}

            if chosen_type == "Selected periods":
                periods = [p for p, var in selected_period_vars.items() if var.get()]
                if not periods:
                    messagebox.showerror("No periods selected", "Please select at least one period.")
                    return None
                return {"date": pd_date, "type": "selected_periods", "periods": periods}

            return {"date": pd_date, "type": "full"}

        def same_pd_entry(a, b) -> bool:
            return normalise_pd_entry(a) == normalise_pd_entry(b)

        def add_selected_pd_day() -> None:
            new_entry = build_new_pd_entry()
            if not new_entry:
                return

            pd_days = self.data.get("pd_days", [])
            already_exists = any(same_pd_entry(item, new_entry) for item in pd_days)

            if not already_exists:
                pd_days.append(new_entry)

            self.data["pd_days"] = pd_days
            save_data(self.data)
            refresh_pd_list()
            self.refresh_all()

        def remove_selected_pd_day() -> None:
            selection = listbox.curselection()
            if not selection:
                messagebox.showerror("No selection", "Select a PD entry to remove.")
                return

            selected_text = listbox.get(selection[0])

            new_list = []
            removed = False

            for item in self.data.get("pd_days", []):
                if not removed and format_pd_entry(item) == selected_text:
                    removed = True
                    continue
                new_list.append(item)

            self.data["pd_days"] = new_list
            save_data(self.data)
            refresh_pd_list()
            self.refresh_all()

        btn_row = tk.Frame(parent, bg=self.theme["panel"])
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            btn_row,
            text="Add PD Entry",
            command=add_selected_pd_day,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row,
            text="Remove Selected",
            command=remove_selected_pd_day,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=10,
            pady=6
        ).pack(side="left")

        refresh_pd_list()

    def save_font_settings(self, section_vars: Dict[str, tk.StringVar]) -> None:
        self.settings.setdefault("font_sections", {})
        for key, var in section_vars.items():
            selected_font = var.get().strip()
            self.settings["font_sections"][key] = selected_font or "Segoe UI"
        save_data(self.data)
        self.refresh_all()
        messagebox.showinfo("Saved", "Font settings saved.")

    def make_scrollable(self, parent: tk.Widget):
        outer = tk.Frame(parent, bg=self.theme["panel"])
        canvas = tk.Canvas(outer, bg=self.theme["panel"], highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.theme["panel"])
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def on_frame_configure(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfigure(window_id, width=event.width)

        scroll_frame.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        return outer, scroll_frame