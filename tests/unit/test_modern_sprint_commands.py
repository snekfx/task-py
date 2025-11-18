"""
Unit tests for modern sprint module commands.

Tests the 6 sprint commands: list, add, remove, clear, stats, init.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from argparse import Namespace

from taskpy.modern.sprint.commands import (
    cmd_sprint,
    _cmd_sprint_list,
    _cmd_sprint_add,
    _cmd_sprint_remove,
    _cmd_sprint_clear,
    _cmd_sprint_stats,
    _cmd_sprint_init,
    _get_sprint_metadata_path,
    _load_sprint_metadata,
    _save_sprint_metadata,
)
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority


class TestSprintMetadataHelpers:
    """Test sprint metadata helper functions."""

    def test_get_sprint_metadata_path(self, tmp_path):
        """Test getting sprint metadata path."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        path = _get_sprint_metadata_path(tmp_path)
        assert path == storage.kanban / "info" / "sprint_current.json"

    def test_load_sprint_metadata_nonexistent(self, tmp_path):
        """Test loading metadata when file doesn't exist."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        metadata = _load_sprint_metadata(tmp_path)
        assert metadata is None

    def test_save_and_load_sprint_metadata(self, tmp_path):
        """Test saving and loading sprint metadata."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        test_metadata = {
            "number": 1,
            "title": "Test Sprint",
            "focus": "Testing",
            "start_date": "2025-11-17",
            "end_date": "2025-12-01",
            "capacity_sp": 20,
            "goals": []
        }

        _save_sprint_metadata(test_metadata, tmp_path)
        loaded = _load_sprint_metadata(tmp_path)

        assert loaded == test_metadata


class TestSprintListCommand:
    """Test _cmd_sprint_list functionality."""

    def test_list_empty_sprint(self, tmp_path, monkeypatch, capsys):
        """Test listing when no tasks in sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_list(args)

        captured = capsys.readouterr()
        # Check for text (may have ANSI codes)
        assert "No" in captured.out and "tasks" in captured.out and "sprint" in captured.out

    def test_list_with_sprint_tasks(self, tmp_path, monkeypatch):
        """Test listing tasks in sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create a task and add to sprint
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Sprint task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=2,
            in_sprint=True
        )
        storage.write_task_file(task)
        storage.rebuild_manifest()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_list(args)


class TestSprintAddCommand:
    """Test _cmd_sprint_add functionality."""

    def test_add_task_to_sprint(self, tmp_path, monkeypatch):
        """Test adding a task to sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_add(args)

        # Verify task is in sprint
        result = storage.find_task_file("TEST-01")
        path, _ = result
        updated_task = storage.read_task_file(path)
        assert updated_task.in_sprint is True

    def test_add_task_already_in_sprint(self, tmp_path, monkeypatch, capsys):
        """Test adding task that's already in sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1,
            in_sprint=True
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_add(args)

        captured = capsys.readouterr()
        # Check for text (may have ANSI codes)
        assert "already" in captured.out and "sprint" in captured.out

    def test_add_nonexistent_task(self, tmp_path, monkeypatch):
        """Test adding a task that doesn't exist."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(task_id="FAKE-99")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _cmd_sprint_add(args)

        assert exc_info.value.code == 1


class TestSprintRemoveCommand:
    """Test _cmd_sprint_remove functionality."""

    def test_remove_task_from_sprint(self, tmp_path, monkeypatch):
        """Test removing a task from sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1,
            in_sprint=True
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_remove(args)

        # Verify task is not in sprint
        result = storage.find_task_file("TEST-01")
        path, _ = result
        updated_task = storage.read_task_file(path)
        assert updated_task.in_sprint is False

    def test_remove_task_not_in_sprint(self, tmp_path, monkeypatch, capsys):
        """Test removing task that's not in sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1,
            in_sprint=False
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_remove(args)

        captured = capsys.readouterr()
        # Check for text (may have ANSI codes)
        assert "not" in captured.out and "sprint" in captured.out


class TestSprintClearCommand:
    """Test _cmd_sprint_clear functionality."""

    def test_clear_empty_sprint(self, tmp_path, monkeypatch, capsys):
        """Test clearing when sprint is empty."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_clear(args)

        captured = capsys.readouterr()
        # Check for text (may have ANSI codes)
        assert "No" in captured.out and "tasks" in captured.out and "sprint" in captured.out

    def test_clear_sprint_with_tasks(self, tmp_path, monkeypatch):
        """Test clearing sprint with multiple tasks."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create multiple tasks in sprint
        for i in range(1, 4):
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1,
                in_sprint=True
            )
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_clear(args)

        # Verify all tasks are removed from sprint
        for i in range(1, 4):
            result = storage.find_task_file(f"TEST-{i:02d}")
            path, _ = result
            task = storage.read_task_file(path)
            assert task.in_sprint is False


class TestSprintStatsCommand:
    """Test _cmd_sprint_stats functionality."""

    def test_stats_empty_sprint(self, tmp_path, monkeypatch, capsys):
        """Test stats when sprint is empty."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_stats(args)

        captured = capsys.readouterr()
        # Check for text (may have ANSI codes)
        assert "No" in captured.out and "tasks" in captured.out and "sprint" in captured.out

    def test_stats_with_tasks(self, tmp_path, monkeypatch, capsys):
        """Test stats with multiple tasks."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks with different statuses and priorities
        tasks_data = [
            ("TEST-01", TaskStatus.BACKLOG, Priority.HIGH, 3),
            ("TEST-02", TaskStatus.ACTIVE, Priority.MEDIUM, 5),
            ("TEST-03", TaskStatus.DONE, Priority.LOW, 2),
        ]

        for task_id, status, priority, sp in tasks_data:
            epic, num = Task.parse_task_id(task_id)
            task = Task(
                id=task_id,
                epic=epic,
                number=num,
                title=f"Task {task_id}",
                status=status,
                priority=priority,
                story_points=sp,
                in_sprint=True
            )
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace()

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_stats(args)

        captured = capsys.readouterr()
        assert "Total Tasks: 3" in captured.out
        assert "Total Story Points: 10" in captured.out


class TestSprintInitCommand:
    """Test _cmd_sprint_init functionality."""

    def test_init_new_sprint(self, tmp_path, monkeypatch):
        """Test initializing a new sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(
            title="Test Sprint",
            focus="Testing",
            duration=14,
            capacity=30,
            force=False
        )

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_init(args)

        # Verify metadata was saved
        metadata = _load_sprint_metadata(tmp_path)
        assert metadata is not None
        assert metadata["title"] == "Test Sprint"
        assert metadata["focus"] == "Testing"
        assert metadata["capacity_sp"] == 30

    def test_init_with_existing_sprint(self, tmp_path, monkeypatch):
        """Test initializing when sprint already exists (without force)."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create existing sprint
        existing = {
            "number": 1,
            "title": "Existing Sprint",
            "focus": "Old work",
            "start_date": "2025-11-01",
            "end_date": "2025-11-15",
            "capacity_sp": 20,
            "goals": []
        }
        _save_sprint_metadata(existing, tmp_path)

        args = Namespace(
            title="New Sprint",
            focus="New work",
            duration=14,
            capacity=30,
            force=False
        )

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _cmd_sprint_init(args)

        assert exc_info.value.code == 1

    def test_init_with_force_overwrites(self, tmp_path, monkeypatch):
        """Test initializing with force flag overwrites existing sprint."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create existing sprint
        existing = {
            "number": 1,
            "title": "Existing Sprint",
            "focus": "Old work",
            "start_date": "2025-11-01",
            "end_date": "2025-11-15",
            "capacity_sp": 20,
            "goals": []
        }
        _save_sprint_metadata(existing, tmp_path)

        args = Namespace(
            title="New Sprint",
            focus="New work",
            duration=14,
            capacity=30,
            force=True
        )

        monkeypatch.chdir(tmp_path)
        _cmd_sprint_init(args)

        # Verify metadata was overwritten
        metadata = _load_sprint_metadata(tmp_path)
        assert metadata["title"] == "New Sprint"
        assert metadata["number"] == 2  # Should increment


# Fixtures
@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create a temporary directory for tests."""
    return tmp_path_factory.mktemp("taskpy_test")
