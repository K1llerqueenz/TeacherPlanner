import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from server import app as server_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server_app, "DB_PATH", str(tmp_path / "planner.db"))
    server_app._FAILED_LOGINS.clear()
    with TestClient(server_app.app) as c:
        yield c


def register(client, username="teacher1", email="t1@example.com", password="correct horse"):
    return client.post("/register", json={"username": username, "email": email, "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_user_and_token(client):
    r = register(client)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["username"] == "teacher1"
    assert body["token"]
    assert client.get("/me", headers=auth(body["token"])).json()["user"]["email"] == "t1@example.com"


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "teacher1", "email": "not-an-email", "password": "long enough"},
        {"username": "teacher1", "email": "a@b.co", "password": "short"},
        {"username": "x", "email": "a@b.co", "password": "long enough"},
    ],
)
def test_register_rejects_bad_details(client, payload):
    assert client.post("/register", json=payload).status_code == 400


def test_duplicate_username_or_email_rejected(client):
    register(client)
    assert register(client, email="other@example.com").status_code == 409
    assert register(client, username="Other", email="T1@example.com").status_code == 409


def test_login_by_username_or_email(client):
    register(client)
    for login in ("teacher1", "TEACHER1", "t1@example.com"):
        r = client.post("/login", json={"login": login, "password": "correct horse"})
        assert r.status_code == 200, login
        assert r.json()["token"]
    assert client.post("/login", json={"login": "teacher1", "password": "wrong"}).status_code == 401
    assert client.post("/login", json={"login": "nobody", "password": "wrong"}).status_code == 401


def test_repeated_failed_logins_are_slowed_down(client):
    register(client)
    for _ in range(server_app.MAX_FAILED_LOGINS):
        client.post("/login", json={"login": "teacher1", "password": "wrong"})
    r = client.post("/login", json={"login": "teacher1", "password": "correct horse"})
    assert r.status_code == 429


def test_requests_without_valid_token_are_refused(client):
    assert client.get("/me").status_code == 401
    assert client.get("/planner", headers=auth("made-up")).status_code == 401
    assert client.put("/planner", json={"data": {}, "base_version": 0}).status_code == 401


def test_logout_ends_the_session(client):
    token = register(client).json()["token"]
    assert client.post("/logout", headers=auth(token)).status_code == 200
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_expired_session_is_refused(client, monkeypatch):
    monkeypatch.setattr(server_app, "SESSION_DAYS", -1)
    token = register(client).json()["token"]
    assert client.get("/me", headers=auth(token)).status_code == 401


def test_change_password_uses_the_session_not_a_user_id(client):
    token_a = register(client).json()["token"]
    token_b = register(client, "teacher2", "t2@example.com", "another password").json()["token"]
    other_device = client.post("/login", json={"login": "teacher1", "password": "correct horse"}).json()["token"]

    # A user_id in the body is ignored: the session decides whose password changes.
    r = client.post(
        "/change-password",
        headers=auth(token_b),
        json={"user_id": "anything", "current_password": "correct horse", "new_password": "new password"},
    )
    assert r.status_code == 400

    r = client.post(
        "/change-password",
        headers=auth(token_a),
        json={"current_password": "correct horse", "new_password": "new password"},
    )
    assert r.status_code == 200
    assert client.post("/login", json={"login": "teacher1", "password": "new password"}).status_code == 200
    # Other devices are signed out, this one stays signed in.
    assert client.get("/me", headers=auth(other_device)).status_code == 401
    assert client.get("/me", headers=auth(token_a)).status_code == 200


def test_planner_round_trip_and_version_check(client):
    token = register(client).json()["token"]
    assert client.get("/planner", headers=auth(token)).json() == {"data": None, "version": 0, "updated_at": None}

    r = client.put("/planner", headers=auth(token), json={"data": {"todos": ["a"]}, "base_version": 0})
    assert r.json()["version"] == 1
    assert client.get("/planner/version", headers=auth(token)).json()["version"] == 1
    assert client.get("/planner", headers=auth(token)).json()["data"] == {"todos": ["a"]}

    # A computer that hasn't seen version 1 can't overwrite it.
    stale = client.put("/planner", headers=auth(token), json={"data": {"todos": []}, "base_version": 0})
    assert stale.status_code == 409
    assert stale.json()["detail"]["version"] == 1
    assert client.get("/planner", headers=auth(token)).json()["data"] == {"todos": ["a"]}


def test_planners_are_private_to_each_account(client):
    token_a = register(client).json()["token"]
    token_b = register(client, "teacher2", "t2@example.com").json()["token"]
    client.put("/planner", headers=auth(token_a), json={"data": {"todos": ["secret"]}, "base_version": 0})
    assert client.get("/planner", headers=auth(token_b)).json()["data"] is None


def test_oversized_planner_rejected(client, monkeypatch):
    monkeypatch.setattr(server_app, "MAX_PLANNER_BYTES", 50)
    token = register(client).json()["token"]
    r = client.put("/planner", headers=auth(token), json={"data": {"x": "y" * 100}, "base_version": 0})
    assert r.status_code == 413
