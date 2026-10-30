import pytest
import requests

from planner_app import auth_api


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self.ok = status < 400
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


@pytest.fixture
def fake_post(monkeypatch):
    calls = []
    state = {"response": FakeResponse(200, {})}

    def post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        if isinstance(state["response"], Exception):
            raise state["response"]
        return state["response"]

    monkeypatch.setattr(auth_api.requests, "post", post)
    state["calls"] = calls
    return state


def test_login_success_strips_login(fake_post):
    fake_post["response"] = FakeResponse(200, {"user": {"id": "u1"}})
    ok, user = auth_api.login_user("  dom  ", "pw")
    assert ok and user == {"id": "u1"}
    call = fake_post["calls"][0]
    assert call["url"] == f"{auth_api.SERVER_URL}/login"
    assert call["json"] == {"login": "dom", "password": "pw"}
    assert call["timeout"] == 10


def test_login_shows_server_error(fake_post):
    fake_post["response"] = FakeResponse(401, {"detail": "Wrong password."})
    assert auth_api.login_user("dom", "bad") == (False, "Wrong password.")


def test_server_error_without_detail(fake_post):
    fake_post["response"] = FakeResponse(500, {})
    assert auth_api.login_user("dom", "pw") == (False, "Something went wrong.")


def test_offline(fake_post):
    fake_post["response"] = requests.ConnectionError()
    assert auth_api.login_user("dom", "pw") == (False, "Could not connect to the server.")


def test_invalid_json(fake_post):
    fake_post["response"] = FakeResponse(502, ValueError("not json"))
    assert auth_api.login_user("dom", "pw") == (False, "Server returned an invalid response.")


def test_register_normalises_email(fake_post):
    fake_post["response"] = FakeResponse(200, {"message": "Welcome", "user": {"id": "u2"}})
    assert auth_api.register_user(" dom ", " Dom@Example.COM ", "pw") == (True, "Welcome", {"id": "u2"})
    assert fake_post["calls"][0]["json"] == {"username": "dom", "email": "dom@example.com", "password": "pw"}


def test_register_failure(fake_post):
    fake_post["response"] = FakeResponse(400, {"detail": "Email taken."})
    assert auth_api.register_user("dom", "a@b.c", "pw") == (False, "Email taken.", None)


def test_change_password(fake_post):
    fake_post["response"] = FakeResponse(200, {})
    assert auth_api.change_password("u1", "old", "new") == (True, "Password updated.")
    assert fake_post["calls"][0]["json"] == {
        "user_id": "u1",
        "current_password": "old",
        "new_password": "new",
    }
