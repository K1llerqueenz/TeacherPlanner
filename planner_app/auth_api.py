from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import requests

SERVER_URL = "https://planner.ventro.it.com"


def _post(path: str, payload: Dict[str, Any]) -> Tuple[bool, Dict[str, Any] | str]:
    url = f"{SERVER_URL}{path}"
    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.RequestException:
        return False, "Could not connect to the server."

    try:
        body = response.json()
    except ValueError:
        return False, "Server returned an invalid response."

    if response.ok:
        return True, body

    return False, body.get("detail", "Something went wrong.")


def register_user(username: str, email: str, password: str) -> tuple[bool, str, dict | None]:
    success, result = _post(
        "/register",
        {
            "username": username.strip(),
            "email": email.strip().lower(),
            "password": password,
        },
    )
    if not success:
        return False, str(result), None

    return True, result.get("message", "Account created."), result.get("user")


def login_user(login_value: str, password: str) -> tuple[bool, dict | str]:
    success, result = _post(
        "/login",
        {
            "login": login_value.strip(),
            "password": password,
        },
    )
    if not success:
        return False, str(result)

    return True, result["user"]


def change_password(user_id: str, current_password: str, new_password: str) -> tuple[bool, str]:
    success, result = _post(
        "/change-password",
        {
            "user_id": user_id,
            "current_password": current_password,
            "new_password": new_password,
        },
    )
    if not success:
        return False, str(result)

    return True, result.get("message", "Password updated.")