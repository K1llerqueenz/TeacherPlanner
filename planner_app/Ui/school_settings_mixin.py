from __future__ import annotations

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk
from typing import Any

from planner_app.storage import save_data
from planner_app.terms import HARDCODED_TERMS, MAX_TERMS, get_term_ranges, get_terms_for_year, validate_terms
from planner_app.timetable import (
    DAYS,
    MAX_PERIODS,
    MIN_PERIODS,
    format_clock,
    get_period_times,
    normalise_period_times,
    parse_clock,
    resize_timetable,
    validate_period_times,
)
from planner_app.Ui.base_app import BaseApp


def next_period_guess(slots: list[dict[str, str]]) -> dict[str, str]:
    """Prefill a new period straight after the last one, the same length as it."""
    if not slots:
        return {"start": "09:00", "end": "10:00"}

    last = slots[-1]
    start = parse_clock(last.get("start"))
    end = parse_clock(last.get("end"))
    if start is None or end is None or end <= start:
        return {"start": last.get("end", ""), "end": ""}

    today = date.today()
    length = datetime.combine(today, end) - datetime.combine(today, start)
    new_end = datetime.combine(today, end) + length
    if new_end.date() != today:
        return {"start": format_clock(end), "end": "23:59"}
    return {"start": format_clock(end), "end": format_clock(new_end.time())}


class SchoolSettingsMixin(BaseApp):
    """Settings > School: bell times, term dates and public holidays."""

    def _build_school_settings(self, parent: tk.Frame) -> None:
        tk.Label(
            parent,
            text="School Settings",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(14, "bold", "popup_text")
        ).pack(anchor="w", padx=12, pady=(12, 6))

        tk.Label(
            parent,
            text="Set up the planner for your school's day and calendar.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w", padx=12, pady=(0, 14))

        bell_body = self._make_section_card(
            parent,
            "Bell Times",
            "How many periods you teach each day, and when each one starts and ends."
        )
        self._build_bell_times_editor(bell_body)

        terms_body = self._make_section_card(
            parent,
            "Term Dates",
            "Your school's term dates. Leave a year on the WA dates or enter your own."
        )
        self._build_term_dates_editor(terms_body)

        holiday_body = self._make_section_card(parent, "Public Holidays")
        self._build_public_holidays_setting(holiday_body)

    def _school_button(self, parent: tk.Widget, text: str, command, primary: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.theme["accent"] if primary else self.theme["outline"],
            fg="white" if primary else self.theme["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "bold", "popup_text"),
            padx=12 if primary else 10,
            pady=8 if primary else 6
        )

    def _reopen_settings_on(self, page: str) -> None:
        self.refresh_all()
        # Rebuild the whole popup so the timetable and PD pages show the new periods.
        self.open_settings_popup(page)

    # -----------------------------
    # Shared forms (also used by first-run setup)
    # -----------------------------
    def _bell_times_form(self, parent: tk.Widget, slots: list[dict[str, str]]):
        """Period count picker plus a start/end row per period. Returns a getter for the times."""
        count_var = tk.StringVar(value=str(len(slots)))
        row_vars: list[dict[str, tk.StringVar]] = []

        top = tk.Frame(parent, bg=self.theme["panel"])
        top.pack(fill="x", pady=(0, 8))

        tk.Label(top, text="Periods per day", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).pack(side="left", padx=(0, 8))

        rows_frame = tk.Frame(parent, bg=self.theme["panel"])
        rows_frame.pack(fill="x")

        def current_slots() -> list[dict[str, str]]:
            return [{"start": v["start"].get().strip(), "end": v["end"].get().strip()} for v in row_vars]

        def render_rows(new_slots: list[dict[str, str]]) -> None:
            for child in rows_frame.winfo_children():
                child.destroy()
            row_vars.clear()

            for col, text in enumerate(["Period", "Starts", "", "Ends"]):
                tk.Label(rows_frame, text=text, bg=self.theme["panel"], fg=self.theme["text"],
                         font=self._font(10, "bold", "popup_text")).grid(row=0, column=col, sticky="w", padx=4)

            for number, slot in enumerate(new_slots, start=1):
                start_var = tk.StringVar(value=slot.get("start", ""))
                end_var = tk.StringVar(value=slot.get("end", ""))
                row_vars.append({"start": start_var, "end": end_var})

                tk.Label(rows_frame, text=f"P{number}", bg=self.theme["panel"], fg=self.theme["text"],
                         font=self._font(10, "bold", "popup_text"), width=6, anchor="w")\
                    .grid(row=number, column=0, sticky="w", padx=4, pady=3)
                tk.Entry(rows_frame, textvariable=start_var, width=8,
                         font=self._font(10, "normal", "popup_text"))\
                    .grid(row=number, column=1, sticky="w", padx=4, pady=3)
                tk.Label(rows_frame, text="to", bg=self.theme["panel"], fg=self.theme["text"],
                         font=self._font(10, "normal", "popup_text"))\
                    .grid(row=number, column=2, padx=4, pady=3)
                tk.Entry(rows_frame, textvariable=end_var, width=8,
                         font=self._font(10, "normal", "popup_text"))\
                    .grid(row=number, column=3, sticky="w", padx=4, pady=3)

        def on_count_change(*_args) -> None:
            text = count_var.get().strip()
            if not text.isdigit():
                return
            wanted = max(MIN_PERIODS, min(MAX_PERIODS, int(text)))
            new_slots = current_slots()[:wanted]
            while len(new_slots) < wanted:
                new_slots.append(next_period_guess(new_slots))
            render_rows(new_slots)

        ttk.Combobox(
            top,
            textvariable=count_var,
            values=[str(i) for i in range(MIN_PERIODS, MAX_PERIODS + 1)],
            state="readonly",
            width=5
        ).pack(side="left")
        count_var.trace_add("write", on_count_change)

        tk.Label(top, text="Use 24-hour times, like 08:40 or 14:50.", bg=self.theme["panel"],
                 fg=self.theme["text"], font=self._font(9, "normal", "popup_text"))\
            .pack(side="left", padx=(14, 0))

        render_rows(slots)
        return current_slots

    def _term_dates_form(self, parent: tk.Widget) -> dict[str, Any]:
        """Editable name/start/end rows. Returns get/set/add callbacks for the rows."""
        row_vars: list[dict[str, tk.StringVar]] = []

        rows_frame = tk.Frame(parent, bg=self.theme["panel"])
        rows_frame.pack(fill="x")

        def current_rows() -> list[dict[str, str]]:
            return [{key: var.get().strip() for key, var in row.items()} for row in row_vars]

        def render_rows(rows: list[dict[str, str]]) -> None:
            for child in rows_frame.winfo_children():
                child.destroy()
            row_vars.clear()

            for col, text in enumerate(["Name", "Starts (YYYY-MM-DD)", "Ends (YYYY-MM-DD)", ""]):
                tk.Label(rows_frame, text=text, bg=self.theme["panel"], fg=self.theme["text"],
                         font=self._font(10, "bold", "popup_text")).grid(row=0, column=col, sticky="w", padx=4)

            for index, row in enumerate(rows, start=1):
                vars_for_row = {key: tk.StringVar(value=row.get(key, "")) for key in ("name", "start", "end")}
                row_vars.append(vars_for_row)

                for col, key in enumerate(("name", "start", "end")):
                    tk.Entry(rows_frame, textvariable=vars_for_row[key], width=14,
                             font=self._font(10, "normal", "popup_text"))\
                        .grid(row=index, column=col, sticky="w", padx=4, pady=3)
                self._school_button(rows_frame, "Remove", lambda i=index - 1: remove_row(i))\
                    .grid(row=index, column=3, sticky="w", padx=4, pady=3)

        def remove_row(index: int) -> None:
            rows = current_rows()
            if 0 <= index < len(rows):
                rows.pop(index)
            render_rows(rows)

        def add_row() -> None:
            rows = current_rows()
            if len(rows) >= MAX_TERMS:
                messagebox.showerror("Too many terms", f"A year can have at most {MAX_TERMS} terms.")
                return
            taken = {row["name"] for row in rows}
            number = len(rows) + 1
            while f"Term {number}" in taken:
                number += 1
            start = ""
            try:
                start = (date.fromisoformat(rows[-1]["end"]) + timedelta(days=14)).isoformat()
            except (IndexError, ValueError):
                pass
            rows.append({"name": f"Term {number}", "start": start, "end": ""})
            render_rows(rows)

        return {"get": current_rows, "set": render_rows, "add": add_row}

    def _term_rows_for_year(self, year: str) -> list[dict[str, str]]:
        ranges = get_term_ranges(get_terms_for_year(int(year), self.settings.get("terms", {})))
        return [{"name": name, "start": start.isoformat(), "end": end.isoformat()} for name, start, end in ranges]

    def _term_rows_to_terms(self, year: str, rows: list[dict[str, str]]) -> tuple[dict[str, Any], str | None]:
        """Turn the form rows into saved term data, or return an error message."""
        names = [row["name"] for row in rows]
        if any(not name for name in names):
            return {}, "Every term needs a name."
        if len({name.casefold() for name in names}) != len(names):
            return {}, "Each term needs a different name."

        year_terms = {row["name"]: {"start": row["start"], "end": row["end"]} for row in rows}
        return year_terms, validate_terms(int(year), year_terms)

    def _uses_default_terms(self, year: str, year_terms: dict[str, Any]) -> bool:
        return year_terms == HARDCODED_TERMS.get(year, {})

    # -----------------------------
    # Bell times
    # -----------------------------
    def _build_bell_times_editor(self, parent: tk.Frame) -> None:
        get_slots = self._bell_times_form(parent, get_period_times(self.settings))

        def save_bell_times() -> None:
            new_slots = get_slots()
            error = validate_period_times(new_slots)
            if error:
                messagebox.showerror("Check your bell times", error)
                return

            new_count = len(new_slots)
            timetable = self.data.setdefault("timetable", {})
            dropped = [
                f"{day} P{entry.get('period')}: {entry.get('label')}"
                for day in DAYS
                for entry in timetable.get(day, [])
                if isinstance(entry.get("period"), int)
                and entry["period"] > new_count
                and entry.get("type") == "class"
                and str(entry.get("label", "")).strip()
            ]
            if dropped:
                listed = "\n".join(dropped[:10]) + ("\n…" if len(dropped) > 10 else "")
                if not messagebox.askyesno(
                    "Remove periods?",
                    f"These lessons are in periods you're removing:\n\n{listed}\n\nRemove them from your timetable?"
                ):
                    return

            self.settings["period_times"] = normalise_period_times(new_slots)
            resize_timetable(timetable, new_count)
            save_data(self.data)
            messagebox.showinfo("Saved", "Bell times saved.")
            self._reopen_settings_on("School")

        btn_row = tk.Frame(parent, bg=self.theme["panel"])
        btn_row.pack(fill="x", pady=(12, 0))
        self._school_button(btn_row, "Save Bell Times", save_bell_times, primary=True).pack(side="left")

    # -----------------------------
    # Term dates
    # -----------------------------
    def _build_term_dates_editor(self, parent: tk.Frame) -> None:
        this_year = date.today().year
        year_options = sorted(
            {str(y) for y in range(this_year - 1, this_year + 6)}
            | set(self.settings.get("terms", {}).keys())
        )
        year_var = tk.StringVar(value=str(this_year))

        top = tk.Frame(parent, bg=self.theme["panel"])
        top.pack(fill="x", pady=(0, 8))

        tk.Label(top, text="Year", bg=self.theme["panel"], fg=self.theme["text"],
                 font=self._font(10, "bold", "popup_text")).pack(side="left", padx=(0, 8))
        ttk.Combobox(top, textvariable=year_var, values=year_options, state="readonly", width=8)\
            .pack(side="left")

        source_label = tk.Label(top, text="", bg=self.theme["panel"], fg=self.theme["text"],
                                font=self._font(9, "normal", "popup_text"))
        source_label.pack(side="left", padx=(14, 0))

        form = self._term_dates_form(parent)

        def load_year(*_args) -> None:
            year = year_var.get()
            rows = self._term_rows_for_year(year)

            if self.settings.get("terms", {}).get(year):
                source_label.config(text="Using your own dates.")
            elif rows:
                source_label.config(text="Using the WA public school dates.")
            else:
                source_label.config(text="No dates set for this year yet. Every day shows as holidays.")

            form["set"](rows)

        def save_terms() -> None:
            year = year_var.get()
            year_terms, error = self._term_rows_to_terms(year, form["get"]())
            if error:
                messagebox.showerror("Check your term dates", error)
                return

            self.settings.setdefault("terms", {})[year] = year_terms
            save_data(self.data)
            messagebox.showinfo("Saved", f"Term dates for {year} saved.")
            self._reopen_settings_on("School")

        def reset_terms() -> None:
            year = year_var.get()
            if year not in self.settings.get("terms", {}):
                load_year()
                return
            default_note = "the WA public school dates" if year in HARDCODED_TERMS else "no term dates"
            if not messagebox.askyesno("Reset term dates?", f"Go back to {default_note} for {year}?"):
                return
            self.settings["terms"].pop(year, None)
            save_data(self.data)
            self._reopen_settings_on("School")

        year_var.trace_add("write", load_year)
        load_year()

        btn_row = tk.Frame(parent, bg=self.theme["panel"])
        btn_row.pack(fill="x", pady=(12, 0))
        self._school_button(btn_row, "Save Term Dates", save_terms, primary=True).pack(side="left", padx=(0, 8))
        self._school_button(btn_row, "Add Term", form["add"]).pack(side="left", padx=(0, 8))
        self._school_button(btn_row, "Use WA Dates", reset_terms).pack(side="left")

    # -----------------------------
    # Public holidays
    # -----------------------------
    def _build_public_holidays_setting(self, parent: tk.Frame) -> None:
        show_var = tk.BooleanVar(value=bool(self.settings.get("show_public_holidays", True)))

        def toggle() -> None:
            self.settings["show_public_holidays"] = bool(show_var.get())
            save_data(self.data)
            self.refresh_all()

        tk.Checkbutton(
            parent,
            text="Show WA public holidays on the planner",
            variable=show_var,
            command=toggle,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            activebackground=self.theme["panel"],
            font=self._font(10, "normal", "popup_text")
        ).pack(anchor="w")

        tk.Label(
            parent,
            text="Turn this off if your school isn't in Western Australia.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(9, "normal", "popup_text")
        ).pack(anchor="w", pady=(4, 0))
