"""Unit tests for modern admin module commands."""

import json
import pytest
import re
from argparse import Namespace
from unittest.mock import patch, MagicMock

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority, VerificationStatus
from taskpy.modern.admin.commands import (
    cmd_init,
    cmd_verify,
    cmd_manifest,
    cmd_groom,
    cmd_session,
)


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_cmd_init_creates_structure(tmp_path, monkeypatch):
    """cmd_init should initialize the kanban structure."""
    monkeypatch.chdir(tmp_path)
    cmd_init(Namespace(force=False, type=None))

    storage = TaskStorage(tmp_path)
    assert storage.kanban.exists()
    assert (storage.kanban / "info" / "config.toml").exists()
    assert (storage.kanban / "manifest.tsv").exists()


@patch('taskpy.modern.admin.commands.subprocess.run')
def test_cmd_verify_updates_status(mock_run, tmp_path, monkeypatch):
    """cmd_verify should run the verification command and persist status."""
    storage = _init_storage(tmp_path)
    task = Task(
        id="TEST-01",
        epic="TEST",
        number=1,
        title="Verification task",
        status=TaskStatus.ACTIVE,
        story_points=3,
    )
    task.verification.command = "echo ok"
    storage.write_task_file(task)

    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

    monkeypatch.chdir(tmp_path)
    cmd_verify(Namespace(task_id="TEST-01", update=True))

    path, _ = storage.find_task_file("TEST-01")
    updated = storage.read_task_file(path)
    assert updated.verification.status == VerificationStatus.PASSED


def test_cmd_manifest_rebuild(tmp_path, monkeypatch):
    """cmd_manifest rebuild should reindex tasks without errors."""
    storage = _init_storage(tmp_path)

    task = Task(
        id="FEAT-01",
        epic="FEAT",
        number=1,
        title="Feature task",
        status=TaskStatus.BACKLOG,
        story_points=2,
    )
    storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_manifest(Namespace(manifest_command='rebuild'))

    assert storage.manifest_file.exists()
    manifest_contents = storage.manifest_file.read_text()
    assert "FEAT-01" in manifest_contents


def test_cmd_groom_identifies_short_stubs(tmp_path, monkeypatch, capsys):
    """cmd_groom should warn when stub tasks lack detail."""
    storage = _init_storage(tmp_path)

    done_task = Task(
        id="DONE-01",
        epic="DONE",
        number=1,
        title="Completed task",
        status=TaskStatus.DONE,
        story_points=3,
        content="x" * 1000,
    )
    storage.write_task_file(done_task)

    stub_task = Task(
        id="STUB-01",
        epic="STUB",
        number=1,
        title="Stub task",
        status=TaskStatus.STUB,
        story_points=1,
        content="short",
    )
    storage.write_task_file(stub_task)

    monkeypatch.chdir(tmp_path)
    cmd_groom(Namespace(ratio=0.5, min_chars=600))

    output = re.sub(r'\x1b\[[0-9;]*m', '', capsys.readouterr().out)
    assert "STUB-01" in output


def test_cmd_session_start_status(tmp_path, monkeypatch, capsys):
    """Session start should create state and status should report it."""
    storage = _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    cmd_session(Namespace(session_command='start', focus="Testing", task="FEAT-01", notes=None))
    capsys.readouterr()  # clear start output
    cmd_session(Namespace(session_command='status'))

    output = re.sub(r'\x1b\[[0-9;]*m', '', capsys.readouterr().out)
    assert "session-001" in output
    assert "Testing" in output

    state_path = storage.kanban / "info" / "session_current.json"
    assert state_path.exists()


def test_cmd_session_commit_and_end(tmp_path, monkeypatch):
    """Ending a session should flush to log and clear state."""
    storage = _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    cmd_session(Namespace(session_command='start', focus=None, task=None, notes=None))
    cmd_session(Namespace(session_command='commit', commit_hash='abc123', message=['Add', 'feature']))
    cmd_session(Namespace(session_command='end', notes="All done"))

    state_path = storage.kanban / "info" / "session_current.json"
    log_path = storage.kanban / "info" / "sessions.jsonl"

    assert not state_path.exists()
    assert log_path.exists()

    lines = [line for line in log_path.read_text().splitlines() if line.strip()]
    assert lines
    record = json.loads(lines[-1])
    assert record["commits"][0]["hash"] == "abc123"
    assert record["notes"].endswith("All done")
    assert record["duration_seconds"] >= 0
