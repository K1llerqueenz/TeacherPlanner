"""Two computers syncing one account through the real server code."""
from types import SimpleNamespace

import pytest

pytest.importorskip("tkinter")
pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from planner_app import auth_api, storage  # noqa: E402
from planner_app.Ui import sync_mixin  # noqa: E402
from server import app as server_app  # noqa: E402


class Computer(sync_mixin.SyncMixin):
    """A planner window without the window."""

    def __init__(self) -> None:  # skip Tk start-up
        self.tk = SimpleNamespace()
        self.data = storage.normalise_data(storage.merge_defaults({}, storage.DEFAULT_DATA))
        self.settings = self.data["settings"]
        self.editor_visible = False
        self.current_overlay = None
        self.days_frame = SimpleNamespace(winfo_exists=lambda: True)
        self.reloads = 0
        self.shown_login = False
        self._sync_busy = False
        self._sync_again = False
        self._sync_job = None
        self._sync_done_callbacks = []
        self.sync_status = "idle"

    # Run network calls straight away instead of on a thread.
    def run_in_background(self, work, on_done):
        on_done(work())

    def after(self, *_args):
        return None

    def after_cancel(self, *_args):
        pass

    def start_main_planner(self):
        self.reloads += 1

    def show_login_screen(self):
        self.shown_login = True

    def sign_in(self, login="teacher1", password="correct horse"):
        ok, user, token = auth_api.login_user(login, password)
        assert ok, user
        storage.set_current_user(self.data, user, token=token)
        self.sync_now(initial=True)


@pytest.fixture
def server(tmp_path, monkeypatch, data_dir):
    monkeypatch.setattr(server_app, "DB_PATH", str(tmp_path / "planner.db"))
    monkeypatch.setattr(sync_mixin, "DATA_DIR", data_dir)
    with TestClient(server_app.app) as client:

        def fake_request(method, url, json=None, headers=None, timeout=None):
            response = client.request(method, url.replace(auth_api.SERVER_URL, ""), json=json, headers=headers)
            response.ok = response.is_success  # the app uses requests, which calls it .ok
            return response

        monkeypatch.setattr(auth_api.requests, "request", fake_request)
        ok, *_ = auth_api.register_user("teacher1", "t1@example.com", "correct horse")
        assert ok
        yield client


@pytest.fixture
def answers(monkeypatch):
    replies = []
    monkeypatch.setattr(sync_mixin.messagebox, "askyesno", lambda *a, **k: replies.pop(0))
    monkeypatch.setattr(sync_mixin.messagebox, "showinfo", lambda *a, **k: None)
    return replies


def test_existing_planner_uploads_then_appears_on_second_computer(server):
    school = Computer()
    school.data["setup"]["completed"] = True
    school.data["todos"].append({"text": "photocopy worksheets"})
    school.sign_in()
    assert school.sync_status == "synced"

    home = Computer()
    home.sign_in()
    assert home.data["todos"] == [{"text": "photocopy worksheets"}]
    assert home.data["setup"]["completed"] is True


def test_changes_flow_both_ways(server):
    school, home = Computer(), Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    home.sign_in()

    home.data["todos"].append({"text": "from home"})
    home.sync_now()
    school.sync_now()
    assert school.data["todos"] == [{"text": "from home"}]
    assert school.reloads == 1

    school.data["todos"].append({"text": "from school"})
    school.sync_now()
    home.sync_now()
    assert [t["text"] for t in home.data["todos"]] == ["from home", "from school"]


def test_no_download_while_editing(server):
    school, home = Computer(), Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    home.sign_in()

    home.data["todos"].append({"text": "new"})
    home.sync_now()

    school.editor_visible = True
    school.sync_now()
    assert school.sync_status == "waiting"
    assert school.data["todos"] == []

    school.editor_visible = False
    school.sync_now()
    assert school.data["todos"] == [{"text": "new"}]


def test_conflict_keep_this_computer(server, answers, data_dir):
    school, home = Computer(), Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    home.sign_in()

    home.data["todos"].append({"text": "home"})
    home.sync_now()
    school.data["todos"].append({"text": "school"})

    answers.append(True)
    school.sync_now()
    assert school.data["todos"] == [{"text": "school"}]
    assert list((data_dir / "backups").glob("planner-from-account-*.json"))

    home.sync_now()
    assert home.data["todos"] == [{"text": "school"}]


def test_conflict_use_account_copy(server, answers, data_dir):
    school, home = Computer(), Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    home.sign_in()

    home.data["todos"].append({"text": "home"})
    home.sync_now()
    school.data["todos"].append({"text": "school"})

    answers.append(False)
    school.sync_now()
    assert school.data["todos"] == [{"text": "home"}]
    assert list((data_dir / "backups").glob("planner-this-computer-*.json"))


def test_offline_keeps_changes_for_later(server, monkeypatch):
    school = Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    school.data["todos"].append({"text": "offline edit"})

    real = auth_api.requests.request

    def no_network(*a, **k):
        raise auth_api.requests.ConnectionError()

    monkeypatch.setattr(auth_api.requests, "request", no_network)
    school.sync_now()
    assert school.sync_status == "offline"

    monkeypatch.setattr(auth_api.requests, "request", real)
    school.sync_now()
    home = Computer()
    home.sign_in()
    assert home.data["todos"] == [{"text": "offline edit"}]


def test_revoked_session_signs_out_but_keeps_local_planner(server, answers):
    school = Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    school.data["todos"].append({"text": "keep me"})

    auth_api.logout(storage.get_session_token(school.data))
    school.sync_now()
    assert school.shown_login
    assert storage.get_current_user(school.data) is None
    assert school.data["todos"] == [{"text": "keep me"}]

    # Signing back in uploads what was kept.
    school.sign_in()
    home = Computer()
    home.sign_in()
    assert home.data["todos"] == [{"text": "keep me"}]


def test_push_now_blocking_on_close(server):
    school = Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    school.data["todos"].append({"text": "last thing"})
    assert school.push_now_blocking(timeout=5)

    home = Computer()
    home.sign_in()
    assert home.data["todos"] == [{"text": "last thing"}]


def test_separate_changes_on_two_computers_merge_without_asking(server, answers):
    school, home = Computer(), Computer()
    school.data["setup"]["completed"] = True
    school.sign_in()
    home.sign_in()

    home.data["pd_days"].append("2026-11-02")
    home.sync_now()
    school.data["todos"].append({"text": "school"})
    school.sync_now()  # no answers queued: a prompt here would fail the test
    assert school.data["pd_days"] == ["2026-11-02"]
    assert school.data["todos"] == [{"text": "school"}]

    home.sync_now()
    assert home.data["todos"] == [{"text": "school"}]
