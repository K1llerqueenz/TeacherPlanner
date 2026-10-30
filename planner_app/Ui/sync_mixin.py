from __future__ import annotations

import queue
import threading
import traceback
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional, Tuple

from planner_app import auth_api
from planner_app.auth_api import ApiResult
from planner_app.settings import get_theme
from planner_app.storage import (
    DATA_DIR,
    DEFAULT_DATA,
    get_current_user,
    get_session_token,
    logout_current_user,
    save_data,
    set_current_user,
)
from planner_app.sync import (
    CONFLICT,
    NOTHING,
    PUSH,
    apply_server_copy,
    get_sync_state,
    has_unsynced_changes,
    mark_synced,
    merge_server_copy,
    plan_sync,
    planner_payload,
    write_backup,
)
from planner_app.Ui.base_app import BaseApp

SYNC_INTERVAL_MS = 30_000


class SyncMixin(BaseApp):
    """Keeps the planner in step with the server without freezing the window.

    Network calls run on a worker thread. Their results come back through a
    queue that the Tk main loop drains, because Tk widgets may only be touched
    from the main thread.
    """

    def _init_sync(self) -> None:
        self._bg_results: "queue.Queue[Tuple[Callable[[Any], None], Any]]" = queue.Queue()
        self._sync_busy = False
        self._sync_again = False
        self._sync_job: Optional[str] = None
        self._sync_done_callbacks: List[Callable[[], None]] = []
        self.sync_status = "idle"
        self.after(100, self._drain_background)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -----------------------------
    # Background work
    # -----------------------------
    def run_in_background(self, work: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        def runner() -> None:
            try:
                result = work()
            except Exception as exc:  # keep the sync loop alive whatever happens
                traceback.print_exc()
                result = ApiResult(False, error=str(exc))
            self._bg_results.put((on_done, result))

        threading.Thread(target=runner, daemon=True).start()

    def _drain_background(self) -> None:
        while True:
            try:
                on_done, result = self._bg_results.get_nowait()
            except queue.Empty:
                break
            try:
                on_done(result)
            except Exception:
                traceback.print_exc()
        self.after(100, self._drain_background)

    # -----------------------------
    # Session
    # -----------------------------
    def _sync_session(self) -> Optional[Tuple[str, str]]:
        user = get_current_user(self.data)
        token = get_session_token(self.data)
        if not user or not token:
            return None
        return user.get("id", ""), token

    def check_session_then_sync(self) -> None:
        session = self._sync_session()
        if session is None:
            return
        _, token = session
        self.run_in_background(lambda: auth_api.get_me(token), lambda r: self._on_session_checked(r, session))

    def _on_session_checked(self, result: ApiResult, session: Tuple[str, str]) -> None:
        if self._sync_session() != session:
            return
        if result.unauthorised:
            self._session_expired()
            return
        if result.ok and isinstance(result.body.get("user"), dict):
            set_current_user(self.data, result.body["user"], auto_login=True)
            save_data(self.data)
            self.sync_now()
        # Offline: carry on with the local planner and try again later.
        self._schedule_sync()

    def _session_expired(self) -> None:
        self._cancel_scheduled_sync()
        # Local planner data stays put. It uploads after the next sign-in.
        logout_current_user(self.data)
        save_data(self.data)
        messagebox.showinfo(
            "Please sign in again",
            "Your sign-in has expired or was ended on another computer.\n\n"
            "Your planner is still saved on this computer.",
        )
        self.show_login_screen()

    # -----------------------------
    # Scheduling
    # -----------------------------
    def _cancel_scheduled_sync(self) -> None:
        if self._sync_job is not None:
            try:
                self.after_cancel(self._sync_job)
            except Exception:
                pass
            self._sync_job = None

    def _schedule_sync(self, delay_ms: int = SYNC_INTERVAL_MS) -> None:
        self._cancel_scheduled_sync()
        self._sync_job = self.after(delay_ms, self._periodic_sync)

    def _periodic_sync(self) -> None:
        self._sync_job = None
        if self._sync_session() is None:
            return
        self.sync_now()
        self._schedule_sync()

    # -----------------------------
    # Sync
    # -----------------------------
    def _on_planner_screen(self) -> bool:
        frame = getattr(self, "days_frame", None)
        try:
            return frame is not None and bool(frame.winfo_exists())
        except Exception:
            return False

    def _busy_editing(self) -> bool:
        return bool(getattr(self, "editor_visible", False) or getattr(self, "current_overlay", None) is not None)

    def sync_now(self, initial: bool = False, on_complete: Optional[Callable[[], None]] = None) -> None:
        """Bring the planner in line with the server.

        `initial` is the sync straight after signing in, before any screen is
        shown, so the server copy can be taken without disturbing the user.
        """
        if on_complete is not None:
            self._sync_done_callbacks.append(on_complete)

        session = self._sync_session()
        if session is None:
            self._finish_sync("signed_out")
            return
        if self._sync_busy:
            self._sync_again = True
            return

        self._sync_busy = True
        user_id, token = session
        self.run_in_background(
            lambda: auth_api.get_planner_version(token),
            lambda r: self._on_server_version(r, session, initial),
        )

    def _finish_sync(self, status: str) -> None:
        self._sync_busy = False
        self.sync_status = status
        callbacks, self._sync_done_callbacks = self._sync_done_callbacks, []
        for callback in callbacks:
            try:
                callback()
            except Exception:
                traceback.print_exc()
        if self._sync_again and self._sync_session() is not None:
            self._sync_again = False
            self.sync_now()

    def _handle_failure(self, result: ApiResult) -> None:
        if result.unauthorised:
            self._finish_sync("signed_out")
            self._session_expired()
        else:
            self._finish_sync("offline" if result.offline else "error")

    def _on_server_version(self, result: ApiResult, session: Tuple[str, str], initial: bool) -> None:
        if self._sync_session() != session:
            self._finish_sync("idle")
            return
        if not result.ok:
            self._handle_failure(result)
            return

        user_id, token = session
        version = int(result.body.get("version", 0))
        action = plan_sync(self.data, user_id, version)

        if action == NOTHING:
            self._finish_sync("synced")
        elif action == PUSH:
            self._push(session, version)
        elif not initial and (not self._on_planner_screen() or self._busy_editing()):
            # Don't swap the planner out from under someone mid-edit.
            self._finish_sync("waiting")
        else:
            self.run_in_background(
                lambda: auth_api.get_planner(token),
                lambda r: self._on_server_copy(r, session, initial, action == CONFLICT),
            )

    def _push(self, session: Tuple[str, str], base_version: int) -> None:
        user_id, token = session
        payload = planner_payload(self.data)
        self.run_in_background(
            lambda: auth_api.put_planner(token, payload, base_version),
            lambda r: self._on_pushed(r, session, payload),
        )

    def _on_pushed(self, result: ApiResult, session: Tuple[str, str], payload: Dict[str, Any]) -> None:
        if self._sync_session() != session:
            self._finish_sync("idle")
            return
        if result.status == 409:
            # Another computer saved first. Go round again to sort it out.
            self._sync_again = True
            self._finish_sync("retry")
            return
        if not result.ok:
            self._handle_failure(result)
            return

        # Records what was sent, so edits made during the upload still count
        # as unsynced.
        mark_synced(self.data, session[0], int(result.body["version"]), payload)
        save_data(self.data)
        self._finish_sync("synced")

    def _on_server_copy(self, result: ApiResult, session: Tuple[str, str], initial: bool, conflict: bool) -> None:
        if self._sync_session() != session:
            self._finish_sync("idle")
            return
        if not result.ok:
            self._handle_failure(result)
            return
        if not initial and (not self._on_planner_screen() or self._busy_editing()):
            self._finish_sync("waiting")
            return

        user_id, _ = session
        server_data = result.body.get("data") or {}
        version = int(result.body.get("version", 0))

        state = get_sync_state(self.data)
        if not conflict and state["user_id"] == user_id and has_unsynced_changes(self.data):
            # Edited here while the server copy was downloading.
            conflict = True

        if not conflict:
            apply_server_copy(self.data, server_data, user_id, version, DEFAULT_DATA)
        elif not merge_server_copy(self.data, server_data, user_id, version, DEFAULT_DATA):
            # Both computers changed different things, so both sets were kept.
            pass
        elif self._ask_keep_this_computer():
            write_backup(DATA_DIR, server_data, "from-account")
            self._push(session, version)
            return
        else:
            write_backup(DATA_DIR, self.data, "this-computer")
            apply_server_copy(self.data, server_data, user_id, version, DEFAULT_DATA)

        save_data(self.data)
        if not initial:
            self._reload_after_pull()
        if has_unsynced_changes(self.data):
            self._push(session, version)
        else:
            self._finish_sync("synced")

    def _ask_keep_this_computer(self) -> bool:
        return messagebox.askyesno(
            "Planner changed in two places",
            "The same part of your planner was changed on this computer and on "
            "another computer since they last synced.\n\n"
            "Keep the version on this computer?\n\n"
            "Yes: keep this computer's version and upload it.\n"
            "No: use the version saved to your account.\n\n"
            f"The version you don't keep is saved as a backup in:\n{DATA_DIR / 'backups'}",
        )

    def _reload_after_pull(self) -> None:
        self.settings = self.data["settings"]
        self.theme = get_theme(self.settings)
        if self._on_planner_screen():
            self.start_main_planner()

    # -----------------------------
    # Sign out and closing
    # -----------------------------
    def push_now_blocking(self, timeout: float) -> bool:
        """Upload unsynced changes straight away. Used when signing out or closing."""
        session = self._sync_session()
        if session is None or not has_unsynced_changes(self.data):
            return True
        state = get_sync_state(self.data)
        if state["user_id"] != session[0]:
            return False

        payload = planner_payload(self.data)
        result = auth_api.put_planner(session[1], payload, state["version"], timeout=timeout)
        if not result.ok:
            return False
        mark_synced(self.data, session[0], int(result.body["version"]), payload)
        save_data(self.data)
        return True

    def end_server_session(self) -> None:
        self._cancel_scheduled_sync()
        token = get_session_token(self.data)
        if token:
            self.run_in_background(lambda: auth_api.logout(token), lambda r: None)

    def _on_close(self) -> None:
        if not self._sync_busy:
            try:
                self.push_now_blocking(timeout=5)
            except Exception:
                traceback.print_exc()
        self.destroy()
