"""Tests for archival command with signoff gating."""

import pytest
from argparse import Namespace

from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.archival.commands import cmd_archive
from taskpy.modern.shared.config import add_signoff_tickets, load_signoff_list, set_feature_flag


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def _make_done_task(storage: TaskStorage, task_id: str):
    task = Task(
        id=task_id,
        epic=task_id.split("-")[0],
        number=int(task_id.split("-")[1]),
        title="Done task",
        status=TaskStatus.DONE,
        priority=Priority.MEDIUM,
        story_points=1,
        content="body",
    )
    storage.write_task_file(task)


def test_archive_requires_signoff_list_when_strict(tmp_path, monkeypatch):
    storage = _init_storage(tmp_path)
    _make_done_task(storage, "TEST-01")
    set_feature_flag("signoff_mode", True, tmp_path)

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cmd_archive(Namespace(task_ids=["TEST-01"], all_done=False, signoff=True, reason=None, yes=True, dry_run=False))

    # Still in done
    _, status = storage.find_task_file("TEST-01")
    assert status == TaskStatus.DONE


def test_archive_with_signoff_strict_mode(tmp_path, monkeypatch):
    storage = _init_storage(tmp_path)
    _make_done_task(storage, "TEST-01")
    set_feature_flag("signoff_mode", True, tmp_path)
    add_signoff_tickets(["TEST-01"], tmp_path)

    monkeypatch.chdir(tmp_path)
    cmd_archive(Namespace(task_ids=["TEST-01"], all_done=False, signoff=True, reason=None, yes=True, dry_run=False))

    path, status = storage.find_task_file("TEST-01")
    assert status == TaskStatus.ARCHIVED
    assert path.exists()
    assert "TEST-01" not in load_signoff_list(tmp_path)


def test_archive_non_strict_requires_reason_if_not_signed_off(tmp_path, monkeypatch):
    storage = _init_storage(tmp_path)
    _make_done_task(storage, "TEST-02")
    set_feature_flag("signoff_mode", False, tmp_path)

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        cmd_archive(Namespace(task_ids=["TEST-02"], all_done=False, signoff=True, reason=None, yes=True, dry_run=False))

    # With reason should work
    cmd_archive(Namespace(task_ids=["TEST-02"], all_done=False, signoff=True, reason="manager approved", yes=True, dry_run=False))
    _, status = storage.find_task_file("TEST-02")
    assert status == TaskStatus.ARCHIVED
