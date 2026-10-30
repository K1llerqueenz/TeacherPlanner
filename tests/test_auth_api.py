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
def fake_request(monkeypatch):
    calls = []
    state = {"response": FakeResponse(200, {})}

    def request(method, url, json=None, headers=None, timeout=None):
        calls.append({"method": method, "url": url, "json": json, "headers": headers, "timeout": timeout})
        if isinstance(state["response"], Exception):
            raise state["response"]
        return state["response"]

    monkeypatch.setattr(auth_api.requests, "request", request)
    state["calls"] = calls
    return state


def test_login_success_strips_login(fake_request):
    fake_request["response"] = FakeResponse(200, {"user": {"id": "u1"}, "token": "tok"})
    assert auth_api.login_user("  dom  ", "pw") == (True, {"id": "u1"}, "tok")
    call = fake_request["calls"][0]
    assert call["method"] == "POST"
    assert call["url"] == f"{auth_api.SERVER_URL}/login"
    assert call["json"] == {"login": "dom", "password": "pw"}
    assert call["headers"] == {}
    assert call["timeout"] == 10


def test_login_shows_server_error(fake_request):
    fake_request["response"] = FakeResponse(401, {"detail": "Wrong password."})
    assert auth_api.login_user("dom", "bad") == (False, "Wrong password.", None)


def test_server_error_without_detail(fake_request):
    fake_request["response"] = FakeResponse(500, {})
    assert auth_api.login_user("dom", "pw") == (False, "Something went wrong.", None)


def test_validation_error_list_is_readable(fake_request):
    fake_request["response"] = FakeResponse(422, {"detail": [{"loc": ["body", "email"]}]})
    ok, message, _ = auth_api.login_user("dom", "pw")
    assert not ok and "valid" in message


def test_offline(fake_request):
    fake_request["response"] = requests.ConnectionError()
    assert auth_api.login_user("dom", "pw") == (False, "Could not connect to the server.", None)
    result = auth_api.get_me("tok")
    assert result.offline and not result.unauthorised


def test_invalid_json(fake_request):
    fake_request["response"] = FakeResponse(502, ValueError("not json"))
    assert auth_api.login_user("dom", "pw") == (False, "Server returned an invalid response.", None)


def test_register_normalises_email(fake_request):
    fake_request["response"] = FakeResponse(200, {"message": "Welcome", "user": {"id": "u2"}, "token": "tok"})
    assert auth_api.register_user(" dom ", " Dom@Example.COM ", "pw") == (True, "Welcome", {"id": "u2"}, "tok")
    assert fake_request["calls"][0]["json"] == {"username": "dom", "email": "dom@example.com", "password": "pw"}


def test_register_failure(fake_request):
    fake_request["response"] = FakeResponse(400, {"detail": "Email taken."})
    assert auth_api.register_user("dom", "a@b.c", "pw") == (False, "Email taken.", None, None)


def test_change_password_sends_the_token_not_a_user_id(fake_request):
    fake_request["response"] = FakeResponse(200, {})
    assert auth_api.change_password("tok", "old", "new") == (True, "Password updated.")
    call = fake_request["calls"][0]
    assert call["headers"] == {"Authorization": "Bearer tok"}
    assert call["json"] == {"current_password": "old", "new_password": "new"}


def test_expired_session_is_flagged(fake_request):
    fake_request["response"] = FakeResponse(401, {"detail": "Please sign in again."})
    result = auth_api.get_planner_version("tok")
    assert result.unauthorised and result.error == "Please sign in again."


def test_conflict_detail_dict_becomes_message(fake_request):
    fake_request["response"] = FakeResponse(409, {"detail": {"message": "Changed elsewhere.", "version": 3}})
    result = auth_api.put_planner("tok", {}, 1)
    assert result.status == 409 and result.error == "Changed elsewhere."
