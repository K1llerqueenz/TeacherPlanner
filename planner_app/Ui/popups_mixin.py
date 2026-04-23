from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from planner_app.reminders import get_reminder_display_lines
from planner_app.storage import save_data
from planner_app.topics import get_class_details, save_class_details
from planner_app.Ui.base_app import BaseApp


class PopupsMixin(BaseApp):
    def _popup_entry(self, parent: tk.Frame, label: str, value: str, key: str,
                     height: int = 1, help_text: str = "") -> None:
        tk.Label(parent, text=label,
                 font=self._font(10, "bold", "popup_text"), bg=self.theme["panel"], fg=self.theme["text"])\
            .pack(anchor="w", pady=(4, 2))
        if help_text:
            tk.Label(parent, text=help_text, font=self._font(8), bg=self.theme["panel"], fg=self.theme["text"])\
                .pack(anchor="w")
        if height == 1:
            widget = tk.Entry(parent, font=self._font(10, "normal", "popup_text"))
            widget.insert(0, value)
            widget.pack(fill="x", pady=(0, 6))
        else:
            widget = tk.Text(parent, font=self._font(10, "normal", "popup_text"), height=height, wrap="word")
            widget.insert("1.0", value)
            widget.pack(fill="x", pady=(0, 6))
        self.class_popup_entries[key] = widget




    def open_topic_prompt(self, week_key: str) -> None:
        if not self.topic_prompt_queue:
            return

        current = self.topic_prompt_queue[self.topic_prompt_index]
        overlay = self.open_overlay()
        popup = tk.Frame(overlay, bg=self.theme["panel"],
                         highlightbackground=self.theme["accent"], highlightthickness=3, padx=16, pady=16)
        popup.place(relx=0.5, rely=0.5, anchor="center", width=420, height=280)

        tk.Label(popup, text="Enter class topic", font=self._font(16, "bold"), bg=self.theme["panel"],
                 fg=self.theme["text"]).pack(anchor="w", pady=(0, 8))
        tk.Label(popup, text=f"{current['day']} • Period {current['period']}\n{current['class_name']}",
                 font=self._font(12, "bold"), bg=self.theme["panel"], fg=self.theme["text"], justify="left")\
            .pack(anchor="w")

        details = get_class_details(self.data, week_key, current["day"], current["period"], current["class_name"])
        entry = tk.Entry(popup, font=self._font(11))
        entry.insert(0, details.get("topic", ""))
        entry.pack(fill="x", pady=(14, 10))
        entry.focus_set()

        progress = tk.Label(popup, text=f"{self.topic_prompt_index + 1} of {len(self.topic_prompt_queue)}",
                            font=self._font(10), bg=self.theme["panel"], fg=self.theme["text"])
        progress.pack(anchor="w")

        button_bar = tk.Frame(popup, bg=self.theme["panel"])
        button_bar.pack(fill="x", side="bottom", pady=(18, 0))

        def skip_prompt() -> None:
            self.close_overlay()

        def next_prompt() -> None:
            topic_text = entry.get().strip()
            if topic_text:
                save_class_details(self.data, week_key, current["day"], current["period"],
                                   current["class_name"], {"topic": topic_text})
                save_data(self.data)
                self.refresh_all()

            self.topic_prompt_index += 1
            if self.topic_prompt_index >= len(self.topic_prompt_queue):
                self.close_overlay()
            else:
                self.open_topic_prompt(week_key)

        tk.Button(button_bar, text="Close", command=skip_prompt, bg=self.theme["outline"],
                  fg=self.theme["text"], relief="flat", font=self._font(10, "bold"), padx=12, pady=8)\
            .pack(side="right", padx=(8, 0))
        tk.Button(button_bar, text="Next", command=next_prompt, bg=self.theme["accent"],
                  fg="white", relief="flat", font=self._font(10, "bold"), padx=12, pady=8)\
            .pack(side="right")
