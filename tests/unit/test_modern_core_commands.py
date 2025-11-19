"""
Unit tests for modern core module commands.

Tests the 5 core CRUD commands: list, show, create, edit, rename.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from taskpy.modern.core.read import cmd_list, cmd_show
from taskpy.modern.core.create import cmd_create
from taskpy.modern.core.edit import cmd_edit
from taskpy.modern.core.rename import cmd_rename
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority


class TestCoreListCommand:
    """Test cmd_list functionality."""

    def test_list_basic(self, tmp_path, monkeypatch):
        """Test basic list command."""
        # Setup test storage
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create a test task
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
        storage.rebuild_manifest()

        # Mock args
        args = Namespace(
            epic=None,
            status=None,
            priority=None,
            milestone=None,
            sprint=False,
            all=False,
            sort='priority'
        )

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Run command (should not raise)
        cmd_list(args)

    def test_list_with_filters(self, tmp_path, monkeypatch):
        """Test list with status filter."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks with different statuses
        for i, status in enumerate([TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.ACTIVE]):
            task = Task(
                id=f"TEST-{i+1:02d}",
                epic="TEST",
                number=i+1,
                title=f"Test task {i+1}",
                status=status,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)
        storage.rebuild_manifest()

        args = Namespace(
            epic=None,
            status='active',
            priority=None,
            milestone=None,
            sprint=False,
            all=False,
            sort='priority'
        )

        monkeypatch.chdir(tmp_path)
        cmd_list(args)


class TestCoreShowCommand:
    """Test cmd_show functionality."""

    def test_show_single_task(self, tmp_path, monkeypatch):
        """Test showing a single task."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.HIGH,
            story_points=3
        )
        storage.write_task_file(task)

        args = Namespace(task_ids=["TEST-01"])

        monkeypatch.chdir(tmp_path)
        cmd_show(args)

    def test_show_multiple_tasks(self, tmp_path, monkeypatch):
        """Test showing multiple tasks."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        for i in range(1, 4):
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        args = Namespace(task_ids=["TEST-01", "TEST-02", "TEST-03"])

        monkeypatch.chdir(tmp_path)
        cmd_show(args)

    def test_show_nonexistent_task(self, tmp_path, monkeypatch, capsys):
        """Test showing a task that doesn't exist."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(task_ids=["FAKE-99"])

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_show(args)

        assert exc_info.value.code == 1


class TestCoreCreateCommand:
    """Test cmd_create functionality."""

    def test_create_basic_task(self, tmp_path, monkeypatch):
        """Test creating a basic task."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(
            epic="TEST",
            title=["Basic", "task"],
            story_points=2,
            priority="medium",
            status="stub",
            tags=None,
            milestone=None,
            edit=False,
            body=None,
            stub=True
        )

        monkeypatch.chdir(tmp_path)
        cmd_create(args)

        # Verify task was created
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert path.exists()

    def test_create_with_story_points(self, tmp_path, monkeypatch):
        """Test creating task with story points."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(
            epic="FEAT",
            title=["New", "feature"],
            story_points=5,
            priority="high",
            status="backlog",
            tags="feature,new",
            milestone="milestone-1",
            edit=False,
            body="Task description",
            stub=False
        )

        monkeypatch.chdir(tmp_path)
        cmd_create(args)

        # Verify task was created with correct SP
        result = storage.find_task_file("FEAT-01")
        assert result is not None
        path, _ = result
        task = storage.read_task_file(path)
        assert task.story_points == 5
        assert task.priority == Priority.HIGH

    def test_create_invalid_epic(self, tmp_path, monkeypatch):
        """Test creating task with invalid epic."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(
            epic="INVALID",
            title=["Test"],
            story_points=1,
            priority="medium",
            status="stub",
            tags=None,
            milestone=None,
            edit=False,
            body=None,
            stub=True
        )

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_create(args)

        assert exc_info.value.code == 1

    def test_create_manual_id(self, tmp_path, monkeypatch):
        """Manual ID creation should succeed when ID is free."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(
            epic="TEST-05",
            title=["Manual", "Task"],
            story_points=1,
            priority="medium",
            status="stub",
            tags=None,
            milestone=None,
            edit=False,
            body=None,
            stub=True,
            auto=False,
        )

        monkeypatch.chdir(tmp_path)
        cmd_create(args)

        result = storage.find_task_file("TEST-05")
        assert result is not None

    def test_create_manual_id_collision_requires_auto(self, tmp_path, monkeypatch):
        """Manual ID should fail without --auto when ID already exists."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        existing = Task(
            id="TEST-05",
            epic="TEST",
            number=5,
            title="Existing task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=1,
        )
        storage.write_task_file(existing)

        args = Namespace(
            epic="TEST-05",
            title=["Conflict"],
            story_points=1,
            priority="medium",
            status="stub",
            tags=None,
            milestone=None,
            edit=False,
            body=None,
            stub=True,
            auto=False,
        )

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            cmd_create(args)
        assert exc_info.value.code == 1

    def test_create_manual_id_auto_bumps(self, tmp_path, monkeypatch):
        """Manual ID with --auto should find the next available number."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        for i in [5, 6]:
            task = Task(
                id=f"TEST-0{i}",
                epic="TEST",
                number=i,
                title=f"Existing {i}",
                status=TaskStatus.STUB,
                priority=Priority.MEDIUM,
                story_points=1,
            )
            storage.write_task_file(task)

        args = Namespace(
            epic="TEST-05",
            title=["Auto", "Bump"],
            story_points=1,
            priority="medium",
            status="stub",
            tags=None,
            milestone=None,
            edit=False,
            body=None,
            stub=True,
            auto=True,
        )

        monkeypatch.chdir(tmp_path)
        cmd_create(args)

        assert storage.find_task_file("TEST-07") is not None


class TestCoreEditCommand:
    """Test cmd_edit functionality."""

    @patch('taskpy.modern.core.edit._open_in_editor')
    def test_edit_existing_task(self, mock_editor, tmp_path, monkeypatch):
        """Test editing an existing task."""
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
        cmd_edit(args)

        # Verify editor was called
        assert mock_editor.called

    def test_edit_nonexistent_task(self, tmp_path, monkeypatch):
        """Test editing a task that doesn't exist."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(task_id="FAKE-99")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_edit(args)

        assert exc_info.value.code == 1


class TestCoreRenameCommand:
    """Test cmd_rename functionality."""

    def test_rename_basic(self, tmp_path, monkeypatch):
        """Test basic task rename."""
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

        args = Namespace(
            old_id="TEST-01",
            new_id="TEST-99",
            force=False,
            skip_manifest=True
        )

        monkeypatch.chdir(tmp_path)
        cmd_rename(args)

        # Verify old task is gone
        assert storage.find_task_file("TEST-01") is None

        # Verify new task exists
        result = storage.find_task_file("TEST-99")
        assert result is not None

    def test_rename_to_existing_id(self, tmp_path, monkeypatch):
        """Test renaming to an ID that already exists."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create two tasks
        for i in [1, 2]:
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        args = Namespace(
            old_id="TEST-01",
            new_id="TEST-02",
            force=False,
            skip_manifest=True
        )

        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cmd_rename(args)

        assert exc_info.value.code == 1

    def test_rename_with_force(self, tmp_path, monkeypatch):
        """Test renaming with force flag to overwrite."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create two tasks
        for i in [1, 2]:
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        args = Namespace(
            old_id="TEST-01",
            new_id="TEST-02",
            force=True,
            skip_manifest=True
        )

        monkeypatch.chdir(tmp_path)
        cmd_rename(args)

        # Verify rename succeeded
        result = storage.find_task_file("TEST-02")
        assert result is not None


# Fixtures
@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create a temporary directory for tests."""
    return tmp_path_factory.mktemp("taskpy_test")
