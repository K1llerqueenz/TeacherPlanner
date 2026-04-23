from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
import webbrowser

from planner_app.Ui.base_app import BaseApp
from planner_app.auth_api import login_user, register_user
from planner_app.storage import (
    get_current_user,
    has_users,
    save_data,
    set_current_user,
    logout_current_user,
    prepare_new_account_local_state,
    user_changed_on_this_device,
)


class LoginMixin(BaseApp):
    def _clear_login_window(self) -> None:
        for child in self.winfo_children():
            child.destroy()

    def _make_auth_card(self, parent: tk.Widget, width: int = 520, height: int = 520) -> tk.Frame:
        shadow = tk.Frame(parent, bg="#dccfd4")
        shadow.place(relx=0.5, rely=0.5, anchor="center", width=width + 10, height=height + 10)

        card = tk.Frame(parent, bg=self.theme["panel"], bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=width, height=height)
        return card

    def _auth_label(self, parent: tk.Widget, text: str, size: int = 10, bold: bool = False) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(size, "bold" if bold else "normal", "popup_text"),
            anchor="w",
            justify="left",
        )

    def _auth_entry(self, parent: tk.Widget, show: str = "") -> tk.Entry:
        return tk.Entry(
            parent,
            font=self._font(11, "normal", "popup_text"),
            bg="white",
            fg=self.theme["text"],
            insertbackground=self.theme["text"],
            relief="solid",
            bd=1,
            show=show,
        )

    def _open_terms_page(self) -> None:
        webbrowser.open("https://ventro.it.com/terms")

    def _toggle_create_button(self, agreed_var: tk.BooleanVar, button: tk.Button) -> None:
        button.config(state="normal" if agreed_var.get() else "disabled")

    def show_login_screen(self) -> None:
        self._clear_login_window()
        self.configure(bg=self.theme["bg"], fg_color=self.theme["bg"])

        outer = tk.Frame(self, bg=self.theme["bg"])
        outer.pack(fill="both", expand=True)

        card = self._make_auth_card(outer, width=540, height=430)

        wrap = tk.Frame(card, bg=self.theme["panel"], padx=36, pady=32)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap,
            text="Teacher Planner",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(24, "bold", "term_title"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        tk.Label(
            wrap,
            text="Sign in with your username or email.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(11, "normal", "popup_text"),
            anchor="w",
        ).pack(fill="x", pady=(0, 24))

        self._auth_label(wrap, "Username or email", bold=True).pack(fill="x", pady=(0, 6))
        login_entry = self._auth_entry(wrap)
        login_entry.pack(fill="x", ipady=8, pady=(0, 14))

        self._auth_label(wrap, "Password", bold=True).pack(fill="x", pady=(0, 6))
        password_entry = self._auth_entry(wrap, show="*")
        password_entry.pack(fill="x", ipady=8, pady=(0, 18))

        button_row = tk.Frame(wrap, bg=self.theme["panel"])
        button_row.pack(fill="x", pady=(6, 0))

        def do_login() -> None:
            login_value = login_entry.get().strip()
            password = password_entry.get()

            if not login_value or not password:
                messagebox.showerror("Missing details", "Please enter your username/email and password.")
                return

            success, result = login_user(login_value, password)
            if not success:
                messagebox.showerror("Login failed", str(result))
                return

            user = result

            switched_user = user_changed_on_this_device(self.data, user)
            if switched_user:
                should_reset = messagebox.askyesno(
                    "Different user detected",
                    "A different account was previously used on this device.\n\n"
                    "Do you want to start with a fresh planner for this account?"
                )
                if should_reset:
                    prepare_new_account_local_state(self.data)

            set_current_user(self.data, user, auto_login=True)
            save_data(self.data)

            setup_info = self.data.get("setup", {})
            if not setup_info.get("completed", False):
                self.show_first_run_setup()
            else:
                self.start_main_planner()

        tk.Button(
            button_row,
            text="Sign in",
            command=do_login,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            font=self._font(10, "bold", "popup_text"),
            padx=14,
            pady=10,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            button_row,
            text="Create account",
            command=self.show_create_account_screen,
            bg=self.theme["outline"],
            fg=self.theme["text"],
            relief="flat",
            font=self._font(10, "bold", "popup_text"),
            padx=14,
            pady=10,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        login_entry.focus_set()
        self.unbind("<Return>")
        self.bind("<Return>", lambda e: do_login())

    def show_create_account_screen(self) -> None:
        self._clear_login_window()
        self.configure(bg=self.theme["bg"], fg_color=self.theme["bg"])

        outer = tk.Frame(self, bg=self.theme["bg"])
        outer.pack(fill="both", expand=True)

        card = self._make_auth_card(outer, width=560, height=610)

        wrap = tk.Frame(card, bg=self.theme["panel"], padx=36, pady=32)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap,
            text="Create account",
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            font=self._font(24, "bold", "term_title"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        tk.Label(
            wrap,
            text="Create your Teacher Planner account.",
            bg=self.theme["panel"],
            fg=self.theme["text"],
            font=self._font(11, "normal", "popup_text"),
            anchor="w",
        ).pack(fill="x", pady=(0, 22))

        self._auth_label(wrap, "Username", bold=True).pack(fill="x", pady=(0, 6))
        username_entry = self._auth_entry(wrap)
        username_entry.pack(fill="x", ipady=8, pady=(0, 12))

        self._auth_label(wrap, "Email", bold=True).pack(fill="x", pady=(0, 6))
        email_entry = self._auth_entry(wrap)
        email_entry.pack(fill="x", ipady=8, pady=(0, 12))

        self._auth_label(wrap, "Password", bold=True).pack(fill="x", pady=(0, 6))
        password_entry = self._auth_entry(wrap, show="*")
        password_entry.pack(fill="x", ipady=8, pady=(0, 12))

        self._auth_label(wrap, "Confirm password", bold=True).pack(fill="x", pady=(0, 6))
        confirm_entry = self._auth_entry(wrap, show="*")
        confirm_entry.pack(fill="x", ipady=8, pady=(0, 16))

        agreed_var = tk.BooleanVar(value=False)

        terms_row = tk.Frame(wrap, bg=self.theme["panel"])
        terms_row.pack(fill="x", pady=(0, 10))

        terms_check = tk.Checkbutton(
            terms_row,
            text="I agree to the Terms and Conditions",
            variable=agreed_var,
            bg=self.theme["panel"],
            fg=self.theme["text"],
            activebackground=self.theme["panel"],
            activeforeground=self.theme["text"],
            selectcolor="white",
            font=self._font(10, "normal", "popup_text"),
            anchor="w",
        )
        terms_check.pack(side="left")

        tk.Button(
            wrap,
            text="View Terms and Conditions",
            command=self._open_terms_page,
            bg=self.theme["panel"],
            fg=self.theme["accent"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=self._font(10, "normal", "popup_text"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 18))

        button_row = tk.Frame(wrap, bg=self.theme["panel"])
        button_row.pack(fill="x", pady=(6, 0))

        def do_create() -> None:
            username = username_entry.get().strip()
            email = email_entry.get().strip()
            password = password_entry.get()
            confirm_password = confirm_entry.get()

            if not username or not email or not password or not confirm_password:
                messagebox.showerror("Missing details", "Please complete all fields.")
                return

            if password != confirm_password:
                messagebox.showerror("Password mismatch", "Your passwords do not match.")
                return

            if not agreed_var.get():
                messagebox.showerror(
                    "Terms required",
                    "You must agree to the Terms and Conditions before creating an account."
                )
                return

            success, message, user = register_user(username, email, password)
            if not success or user is None:
                messagebox.showerror("Could not create account", message)
                return

            set_current_user(self.data, user, auto_login=True)
            prepare_new_account_local_state(self.data)
            save_data(self.data)

            messagebox.showinfo("Account created", "Your account has been created.")
            self.show_first_run_setup()

        if has_users(self.data):
            tk.Button(
                button_row,
                text="Back to sign in",
                command=self.show_login_screen,
                bg=self.theme["outline"],
                fg=self.theme["text"],
                relief="flat",
                font=self._font(10, "bold", "popup_text"),
                padx=14,
                pady=10,
                cursor="hand2",
            ).pack(side="left")

        create_button = tk.Button(
            button_row,
            text="Create account",
            command=do_create,
            bg=self.theme["accent"],
            fg="white",
            relief="flat",
            font=self._font(10, "bold", "popup_text"),
            padx=14,
            pady=10,
            cursor="hand2",
            state="disabled",
        )
        create_button.pack(side="right")

        terms_check.config(command=lambda: self._toggle_create_button(agreed_var, create_button))

        username_entry.focus_set()
        self.unbind("<Return>")
        self.bind("<Return>", lambda e: do_create())
    def logout_user(self) -> None:
        current_user = get_current_user(self.data)
        if current_user is None:
            self.show_login_screen()
            return

        if not messagebox.askyesno("Log out", "Do you want to log out of Teacher Planner?"):
            return

        logout_current_user(self.data)
        save_data(self.data)
        self.show_login_screen()