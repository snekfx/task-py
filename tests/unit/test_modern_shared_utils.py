"""Tests for modern shared utils."""

import argparse
import pytest

from taskpy.legacy.models import Task, TaskStatus, Priority, HistoryEntry, utc_now
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.shared.utils import (
    add_reason_argument,
    format_history_entry,
    load_task_or_exit,
    require_initialized,
)


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_require_initialized_raises(tmp_path):
    storage = TaskStorage(tmp_path)
    with pytest.raises(SystemExit):
        require_initialized(storage)


def test_load_task_or_exit_returns_task(tmp_path):
    storage = _init_storage(tmp_path)
    task = Task(
        id="UTIL-01",
        epic="UTIL",
        number=1,
        title="Utils test",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        story_points=1,
    )
    storage.write_task_file(task)

    loaded, path, status = load_task_or_exit(storage, "UTIL-01")
    assert loaded.id == "UTIL-01"
    assert status == TaskStatus.BACKLOG
    assert path.exists()


def test_format_history_entry_includes_transition():
    entry = HistoryEntry(
        timestamp=utc_now(),
        action="promote",
        from_status="backlog",
        to_status="ready",
        reason="Test pass",
        actor="agent",
        metadata={"note": "hello"},
    )
    lines = format_history_entry(entry)
    assert "backlog" in lines[0]
    assert any("Reason" in line for line in lines)


def test_add_reason_argument():
    parser = argparse.ArgumentParser()
    add_reason_argument(parser, required=True, help_text="Need reason")
    with pytest.raises(SystemExit):
        parser.parse_args([])
    args = parser.parse_args(["--reason", "because"])
    assert args.reason == "because"
