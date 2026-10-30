from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests

SERVER_URL = os.environ.get("TEACHERPLANNER_SERVER_URL", "https://planner.ventro.it.com").rstrip("/")
TIMEOUT = 10


@dataclass
class ApiResult:
    ok: bool
    status: int = 0
    body: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def offline(self) -> bool:
        # No answer from the server at all (no wifi, server down).
        return not self.ok and self.status == 0

    @property
    def unauthorised(self) -> bool:
        return self.status == 401


def _request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: float = TIMEOUT,
) -> ApiResult:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        response = requests.request(
            method, f"{SERVER_URL}{path}", json=payload, headers=headers, timeout=timeout
        )
    except requests.RequestException:
        return ApiResult(False, error="Could not connect to the server.")

    try:
        body = response.json()
    except ValueError:
        return ApiResult(False, response.status_code, error="Server returned an invalid response.")
    if not isinstance(body, dict):
        body = {}

    if response.ok:
        return ApiResult(True, response.status_code, body)

    detail = body.get("detail", "Something went wrong.")
    if isinstance(detail, dict):
        detail = detail.get("message", "Something went wrong.")
    elif not isinstance(detail, str):
        # FastAPI validation errors come back as a list.
        detail = "Some of the details you entered aren't valid."
    return ApiResult(False, response.status_code, body, detail)


def register_user(username: str, email: str, password: str) -> tuple[bool, str, dict | None, str | None]:
    result = _request(
        "POST",
        "/register",
        {
            "username": username.strip(),
            "email": email.strip().lower(),
            "password": password,
        },
    )
    if not result.ok:
        return False, result.error, None, None

    return True, result.body.get("message", "Account created."), result.body.get("user"), result.body.get("token")


def login_user(login_value: str, password: str) -> tuple[bool, dict | str, str | None]:
    result = _request(
        "POST",
        "/login",
        {
            "login": login_value.strip(),
            "password": password,
        },
    )
    if not result.ok:
        return False, result.error, None

    return True, result.body["user"], result.body.get("token")


def get_me(token: str) -> ApiResult:
    return _request("GET", "/me", token=token)


def logout(token: str) -> ApiResult:
    return _request("POST", "/logout", token=token, timeout=5)


def change_password(token: str, current_password: str, new_password: str) -> tuple[bool, str]:
    result = _request(
        "POST",
        "/change-password",
        {
            "current_password": current_password,
            "new_password": new_password,
        },
        token=token,
    )
    if not result.ok:
        return False, result.error

    return True, result.body.get("message", "Password updated.")


def get_planner_version(token: str) -> ApiResult:
    return _request("GET", "/planner/version", token=token)


def get_planner(token: str) -> ApiResult:
    return _request("GET", "/planner", token=token, timeout=30)


def put_planner(token: str, data: Dict[str, Any], base_version: int, timeout: float = 30) -> ApiResult:
    return _request("PUT", "/planner", {"data": data, "base_version": base_version}, token=token, timeout=timeout)
