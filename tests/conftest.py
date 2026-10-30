import os
import tempfile

import pytest

# Keep tests away from the real per-user data folder.
os.environ.setdefault("TEACHERPLANNER_DATA_DIR", tempfile.mkdtemp(prefix="teacherplanner-tests-"))

from planner_app import storage  # noqa: E402


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", tmp_path)
    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "data.json")
    monkeypatch.setattr(storage, "BACKUP_FILE", tmp_path / "data.json.bak")
    monkeypatch.setattr(storage, "LEGACY_DATA_FILE", tmp_path / "legacy" / "data.json")
    return tmp_path
