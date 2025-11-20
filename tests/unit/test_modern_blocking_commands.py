"""Unit tests for modern blocking commands."""

from argparse import Namespace
from pathlib import Path
import re

import pytest

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.modern.blocking.commands import cmd_block, cmd_unblock


def _init_storage(tmp_path: Path) -> TaskStorage:
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_block_moves_task_to_blocked(tmp_path, monkeypatch):
    """Blocking a task should move it to blocked and persist reason."""
    storage = _init_storage(tmp_path)
    task = Task(
        id="TEST-01",
        epic="TEST",
        number=1,
        title="Block me",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        story_points=1,
    )
    storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_block(Namespace(task_ids=["TEST-01"], reason="Waiting on dependency"))

    path, status = storage.find_task_file("TEST-01")
    assert status == TaskStatus.BLOCKED
    blocked_task = storage.read_task_file(path)
    assert blocked_task.blocked_reason == "Waiting on dependency"


def test_block_already_blocked(tmp_path, monkeypatch, capsys):
    """Blocking an already blocked task should be a no-op."""
    storage = _init_storage(tmp_path)
    task = Task(
        id="TEST-02",
        epic="TEST",
        number=2,
        title="Already blocked",
        status=TaskStatus.BLOCKED,
        priority=Priority.MEDIUM,
        story_points=1,
        blocked_reason="Prior blocker",
    )
    storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_block(Namespace(task_ids=["TEST-02"], reason="Another reason"))

    output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "already blocked" in output


def test_unblock_moves_back_to_backlog(tmp_path, monkeypatch):
    """Unblocking a blocked task should send it to backlog and clear reason."""
    storage = _init_storage(tmp_path)
    task = Task(
        id="TEST-03",
        epic="TEST",
        number=3,
        title="Release me",
        status=TaskStatus.BLOCKED,
        priority=Priority.MEDIUM,
        story_points=2,
        blocked_reason="Data pipeline down",
    )
    storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_unblock(Namespace(task_ids=["TEST-03"]))

    path, status = storage.find_task_file("TEST-03")
    assert status == TaskStatus.BACKLOG
    unblocked = storage.read_task_file(path)
    assert unblocked.blocked_reason is None


def test_unblock_non_blocked(tmp_path, monkeypatch, capsys):
    """Unblocking a non-blocked task should print a message and exit cleanly."""
    storage = _init_storage(tmp_path)
    task = Task(
        id="TEST-04",
        epic="TEST",
        number=4,
        title="Fine task",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        story_points=1,
    )
    storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_unblock(Namespace(task_ids=["TEST-04"]))

    output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "is not blocked" in output


def test_block_multiple_tasks(tmp_path, monkeypatch):
    """Blocking multiple tasks with comma separation should work."""
    storage = _init_storage(tmp_path)
    for i in range(2):
        task = Task(
            id=f"TEST-0{i+1}",
            epic="TEST",
            number=i + 1,
            title="Task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1,
        )
        storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_block(Namespace(task_ids=["TEST-01,TEST-02"], reason="Audit"))

    for tid in ["TEST-01", "TEST-02"]:
        path, status = storage.find_task_file(tid)
        assert status == TaskStatus.BLOCKED


def test_unblock_multiple_tasks(tmp_path, monkeypatch):
    """Unblocking multiple tasks should process each ID."""
    storage = _init_storage(tmp_path)
    for i in range(2):
        task = Task(
            id=f"TEST-0{i+1}",
            epic="TEST",
            number=i + 1,
            title="Task",
            status=TaskStatus.BLOCKED,
            priority=Priority.MEDIUM,
            story_points=1,
            blocked_reason="down",
        )
        storage.write_task_file(task)

    monkeypatch.chdir(tmp_path)
    cmd_unblock(Namespace(task_ids=["TEST-01", "TEST-02"]))

    for tid in ["TEST-01", "TEST-02"]:
        path, status = storage.find_task_file(tid)
        assert status == TaskStatus.BACKLOG
