"""Teacher Planner account and sync server.

Accounts, sign-in sessions and each teacher's planner live in one SQLite file.
The desktop app gets a session token when it signs in and sends it with every
request, so the server always knows who is asking.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

DB_PATH = os.environ.get("PLANNER_DB_PATH", "planner.db")
SESSION_DAYS = int(os.environ.get("PLANNER_SESSION_DAYS", "60"))
MAX_PLANNER_BYTES = int(os.environ.get("PLANNER_MAX_BYTES", str(5 * 1024 * 1024)))
MIN_PASSWORD_LENGTH = 8

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS planners (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)


# -----------------------------
# Passwords and tokens
# -----------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


# Spent on unknown usernames too, so response time doesn't reveal which accounts exist.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(conn: sqlite3.Connection, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), user_id, _iso(now), _iso(now + timedelta(days=SESSION_DAYS))),
    )
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_iso(now),))
    return token


def _public_user(row: sqlite3.Row) -> Dict[str, str]:
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


# -----------------------------
# Simple sign-in rate limit
# -----------------------------
_FAILED_LOGINS: Dict[str, list[float]] = {}
_FAILED_LOCK = threading.Lock()
MAX_FAILED_LOGINS = 10
FAILED_WINDOW_SECONDS = 15 * 60


def _too_many_failures(key: str) -> bool:
    cutoff = time.monotonic() - FAILED_WINDOW_SECONDS
    with _FAILED_LOCK:
        attempts = [t for t in _FAILED_LOGINS.get(key, []) if t > cutoff]
        _FAILED_LOGINS[key] = attempts
        return len(attempts) >= MAX_FAILED_LOGINS


def _record_failure(key: str) -> None:
    with _FAILED_LOCK:
        _FAILED_LOGINS.setdefault(key, []).append(time.monotonic())


# -----------------------------
# App
# -----------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Teacher Planner server", lifespan=lifespan)


class RegisterIn(BaseModel):
    username: str
    email: str
    password: str


class LoginIn(BaseModel):
    login: str
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class PlannerIn(BaseModel):
    data: Dict[str, Any]
    base_version: int


def current_session(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please sign in again.")
    token = authorization.split(" ", 1)[1].strip()
    with db() as conn:
        row = conn.execute(
            """
            SELECT users.*, sessions.token_hash, sessions.expires_at
            FROM sessions JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (_token_hash(token),),
        ).fetchone()
    if row is None or row["expires_at"] < _iso(_now()):
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return {"user": _public_user(row), "token_hash": row["token_hash"]}


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Passwords need at least {MIN_PASSWORD_LENGTH} characters.",
        )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/register")
def register(body: RegisterIn) -> Dict[str, Any]:
    username = body.username.strip()
    email = body.email.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Usernames need 3 to 32 letters, numbers, dots, dashes or underscores.",
        )
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    _validate_password(body.password)

    user_id = str(uuid.uuid4())
    with db() as conn:
        taken = conn.execute(
            "SELECT username, email FROM users WHERE username = ? OR email = ?", (username, email)
        ).fetchone()
        if taken is not None:
            field = "username" if taken["username"].lower() == username.lower() else "email"
            raise HTTPException(status_code=409, detail=f"That {field} is already in use.")
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, email, hash_password(body.password), _iso(_now())),
        )
        token = create_session(conn, user_id)

    return {
        "message": "Account created.",
        "user": {"id": user_id, "username": username, "email": email},
        "token": token,
    }


@app.post("/login")
def login(body: LoginIn, request: Request) -> Dict[str, Any]:
    login_value = body.login.strip()
    client = request.client.host if request.client else "?"
    limit_key = f"{client}|{login_value.lower()}"
    if _too_many_failures(limit_key):
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait a few minutes.")

    with db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?", (login_value, login_value.lower())
        ).fetchone()
        if row is None:
            verify_password(body.password, _DUMMY_HASH)
            ok = False
        else:
            ok = verify_password(body.password, row["password_hash"])
        if not ok:
            _record_failure(limit_key)
            raise HTTPException(status_code=401, detail="Incorrect username/email or password.")
        token = create_session(conn, row["id"])

    return {"user": _public_user(row), "token": token}


@app.get("/me")
def me(session: Dict[str, Any] = Depends(current_session)) -> Dict[str, Any]:
    return {"user": session["user"]}


@app.post("/logout")
def logout(session: Dict[str, Any] = Depends(current_session)) -> Dict[str, str]:
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (session["token_hash"],))
    return {"message": "Signed out."}


@app.post("/change-password")
def change_password(
    body: ChangePasswordIn, session: Dict[str, Any] = Depends(current_session)
) -> Dict[str, str]:
    user_id = session["user"]["id"]
    _validate_password(body.new_password)
    with db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None or not verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Your current password is incorrect.")
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(body.new_password), user_id),
        )
        # Sign out every other device, keep this one.
        conn.execute(
            "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
            (user_id, session["token_hash"]),
        )
    return {"message": "Password updated."}


@app.get("/planner")
def get_planner(session: Dict[str, Any] = Depends(current_session)) -> Dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT data, version, updated_at FROM planners WHERE user_id = ?",
            (session["user"]["id"],),
        ).fetchone()
    if row is None:
        return {"data": None, "version": 0, "updated_at": None}
    return {"data": json.loads(row["data"]), "version": row["version"], "updated_at": row["updated_at"]}


@app.get("/planner/version")
def get_planner_version(session: Dict[str, Any] = Depends(current_session)) -> Dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT version, updated_at FROM planners WHERE user_id = ?", (session["user"]["id"],)
        ).fetchone()
    if row is None:
        return {"version": 0, "updated_at": None}
    return {"version": row["version"], "updated_at": row["updated_at"]}


@app.put("/planner")
def put_planner(body: PlannerIn, session: Dict[str, Any] = Depends(current_session)) -> Dict[str, Any]:
    encoded = json.dumps(body.data, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_PLANNER_BYTES:
        raise HTTPException(status_code=413, detail="Planner data is too large to sync.")

    user_id = session["user"]["id"]
    updated_at = _iso(_now())
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT version FROM planners WHERE user_id = ?", (user_id,)).fetchone()
        current = row["version"] if row else 0
        if body.base_version != current:
            # Another computer saved since this one last synced.
            raise HTTPException(
                status_code=409,
                detail={"message": "The planner changed on another computer.", "version": current},
            )
        new_version = current + 1
        conn.execute(
            """
            INSERT INTO planners (user_id, data, version, updated_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                data = excluded.data, version = excluded.version, updated_at = excluded.updated_at
            """,
            (user_id, encoded, new_version, updated_at),
        )
    return {"version": new_version, "updated_at": updated_at}
