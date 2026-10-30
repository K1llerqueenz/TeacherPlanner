"""Decides how to bring the local planner and the server copy back in line.

Everything here works on the planner dict only, so it can be tested without a
window or a network. The UI runs the network calls in `Ui/sync_mixin.py`.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Kept on this computer only, never uploaded.
LOCAL_ONLY_KEYS = ("auth", "sync")

NOTHING = "nothing"
PUSH = "push"
PULL = "pull"
CONFLICT = "conflict"


def get_sync_state(data: Dict[str, Any]) -> Dict[str, Any]:
    state = data.setdefault("sync", {})
    state.setdefault("user_id", None)
    state.setdefault("version", 0)
    state.setdefault("synced_hash", "")
    state.setdefault("last_synced_at", "")
    # The planner as it was at the last sync, so changes made on two
    # computers can be told apart and combined.
    state.setdefault("base", None)
    return state


def planner_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: deepcopy(value) for key, value in data.items() if key not in LOCAL_ONLY_KEYS}


def payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def has_unsynced_changes(data: Dict[str, Any]) -> bool:
    return payload_hash(planner_payload(data)) != get_sync_state(data)["synced_hash"]


def is_blank_planner(data: Dict[str, Any]) -> bool:
    return (
        not data.get("setup", {}).get("completed", False)
        and not data.get("todos")
        and not data.get("weekly_classes")
        and not data.get("assignments")
    )


def plan_sync(data: Dict[str, Any], user_id: str, server_version: int) -> str:
    state = get_sync_state(data)

    if state["user_id"] != user_id:
        # This account has never synced on this computer.
        if server_version == 0:
            return PUSH
        if is_blank_planner(data):
            return PULL
        return CONFLICT

    local_changed = has_unsynced_changes(data)
    server_changed = server_version != state["version"]
    if local_changed and server_changed:
        return CONFLICT
    if local_changed:
        return PUSH
    if server_changed:
        return PULL
    return NOTHING


def mark_synced(data: Dict[str, Any], user_id: str, version: int, payload: Dict[str, Any]) -> None:
    state = get_sync_state(data)
    state["user_id"] = user_id
    state["version"] = version
    state["synced_hash"] = payload_hash(payload)
    state["base"] = deepcopy(payload)
    state["last_synced_at"] = datetime.now().isoformat(timespec="seconds")


_MISSING = object()


def merge_three_way(base: Any, local: Any, remote: Any, path: str = "") -> Tuple[Any, List[str]]:
    """Combine changes made here and on another computer since `base`.

    A value changed on one side only takes that change. Dicts are combined key
    by key. Anything else changed differently on both sides is a conflict,
    returned by path, and the local value is kept for it.
    """
    if local == remote:
        return local, []
    if local == base:
        return remote, []
    if remote == base:
        return local, []
    if isinstance(local, dict) and isinstance(remote, dict):
        base_dict = base if isinstance(base, dict) else {}
        merged: Dict[str, Any] = {}
        conflicts: List[str] = []
        for key in list(local) + [k for k in remote if k not in local]:
            value, key_conflicts = merge_three_way(
                base_dict.get(key, _MISSING),
                local.get(key, _MISSING),
                remote.get(key, _MISSING),
                f"{path}/{key}",
            )
            conflicts.extend(key_conflicts)
            if value is not _MISSING:
                merged[key] = value
        return merged, conflicts
    return local, [path or "/"]


def _replace_planner(data: Dict[str, Any], incoming: Dict[str, Any], defaults: Dict[str, Any]) -> None:
    from planner_app.storage import merge_defaults, normalise_data

    local_only = {key: data[key] for key in LOCAL_ONLY_KEYS if key in data}
    incoming = {key: value for key, value in incoming.items() if key not in LOCAL_ONLY_KEYS}
    data.clear()
    data.update(normalise_data(merge_defaults(deepcopy(incoming), defaults)))
    data.update(local_only)


def apply_server_copy(
    data: Dict[str, Any],
    server_data: Dict[str, Any],
    user_id: str,
    version: int,
    defaults: Dict[str, Any],
) -> None:
    """Replace the local planner with the server copy, in place."""
    _replace_planner(data, server_data, defaults)
    # Filling in missing defaults locally doesn't count as a change to upload.
    mark_synced(data, user_id, version, planner_payload(data))


def merge_server_copy(
    data: Dict[str, Any],
    server_data: Dict[str, Any],
    user_id: str,
    version: int,
    defaults: Dict[str, Any],
) -> List[str]:
    """Fold the server copy into the local planner, keeping changes from both.

    Returns the conflicting paths and leaves `data` alone if there are any.
    Otherwise `data` holds the combined planner, marked as based on `version`,
    so anything this computer added still counts as unsynced and uploads.
    """
    state = get_sync_state(data)
    base = state["base"] if state["user_id"] == user_id and state["base"] is not None else {}
    local = planner_payload(data)
    remote = {key: value for key, value in server_data.items() if key not in LOCAL_ONLY_KEYS}

    merged, conflicts = merge_three_way(base, local, remote)
    if conflicts:
        return conflicts

    apply_server_copy(data, remote, user_id, version, defaults)
    _replace_planner(data, merged, defaults)
    return []


def write_backup(directory: Path, data: Dict[str, Any], label: str) -> Optional[Path]:
    """Save a copy of a planner before it gets replaced, so nothing is lost."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = directory / "backups" / f"planner-{label}-{stamp}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(planner_payload(data), f, indent=2)
    except OSError:
        return None
    return path
