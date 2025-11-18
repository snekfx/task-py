"""
Unit tests for modern display module commands.

Tests the 5 display commands: info, stoplight, kanban, history, stats.
"""

import pytest
import sys
import re
from pathlib import Path
from unittest.mock import Mock, patch
from argparse import Namespace

from taskpy.modern.display.commands import (
    cmd_info,
    cmd_stoplight,
    cmd_kanban,
    cmd_history,
    cmd_stats,
)
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority, HistoryEntry, VerificationStatus, utc_now


class TestInfoCommand:
    """Test cmd_info functionality."""

    def test_info_shows_gate_requirements(self, tmp_path, monkeypatch, capsys):
        """Test info command shows gate requirements."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=0,  # Missing - should show in requirements
            content="Short"  # Too short - should show in requirements
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        cmd_info(args)

        captured = capsys.readouterr()
        # Remove ANSI codes for easier testing
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "TEST-01" in output
        assert "stub" in output.lower()
        assert "backlog" in output.lower()  # Next status

    def test_info_for_done_task(self, tmp_path, monkeypatch, capsys):
        """Test info command for task at final status."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.DONE,
            priority=Priority.MEDIUM,
            story_points=3
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        cmd_info(args)

        captured = capsys.readouterr()
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "final status" in output.lower()


class TestStoplightCommand:
    """Test cmd_stoplight functionality."""

    def test_stoplight_exit_0_when_ready(self, tmp_path, monkeypatch):
        """Test stoplight exits 0 when ready to promote."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=3,
            content="This is a detailed description with enough content"
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            cmd_stoplight(args)

        assert exc_info.value.code == 0

    def test_stoplight_exit_1_when_missing_requirements(self, tmp_path, monkeypatch):
        """Test stoplight exits 1 when missing requirements."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=0,  # Missing
            content="Short"  # Too short
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            cmd_stoplight(args)

        assert exc_info.value.code == 1

    def test_stoplight_exit_2_when_blocked(self, tmp_path, monkeypatch):
        """Test stoplight exits 2 when task is blocked."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BLOCKED,
            priority=Priority.MEDIUM,
            story_points=3,
            blocked_reason="Waiting on API"
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            cmd_stoplight(args)

        assert exc_info.value.code == 2

    def test_stoplight_exit_2_when_not_found(self, tmp_path, monkeypatch):
        """Test stoplight exits 2 when task not found."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(task_id="NONEXISTENT")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            cmd_stoplight(args)

        assert exc_info.value.code == 2


class TestKanbanCommand:
    """Test cmd_kanban functionality."""

    def test_kanban_displays_all_columns(self, tmp_path, monkeypatch):
        """Test kanban command displays all status columns."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks in different statuses
        for i, status in enumerate([TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.ACTIVE]):
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Task {i}",
                status=status,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace(epic=None, sort='priority')

        monkeypatch.chdir(tmp_path)
        cmd_kanban(args)
        # Just verify it doesn't crash

    def test_kanban_filter_by_epic(self, tmp_path, monkeypatch, capsys):
        """Test kanban command filters by epic."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks in different epics
        task1 = Task(
            id="FEAT-01",
            epic="FEAT",
            number=1,
            title="Feature task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=2
        )
        task2 = Task(
            id="BUGS-01",
            epic="BUGS",
            number=1,
            title="Bug task",
            status=TaskStatus.BACKLOG,
            priority=Priority.HIGH,
            story_points=1
        )
        storage.write_task_file(task1)
        storage.write_task_file(task2)
        storage.rebuild_manifest()

        args = Namespace(epic="FEAT", sort='priority')

        monkeypatch.chdir(tmp_path)
        cmd_kanban(args)

        captured = capsys.readouterr()
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "FEAT-01" in output
        # BUGS-01 should not appear when filtering by FEAT


class TestHistoryCommand:
    """Test cmd_history functionality."""

    def test_history_single_task(self, tmp_path, monkeypatch, capsys):
        """Test history command for single task."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=3
        )

        # Add some history
        task.history.append(HistoryEntry(
            timestamp=utc_now(),
            action="create",
            from_status=None,
            to_status="stub",
            reason=None
        ))
        task.history.append(HistoryEntry(
            timestamp=utc_now(),
            action="promote",
            from_status="stub",
            to_status="backlog",
            reason=None
        ))

        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", all=False)

        monkeypatch.chdir(tmp_path)
        cmd_history(args)

        captured = capsys.readouterr()
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "TEST-01" in output
        assert "create" in output
        assert "promote" in output
        assert "stub" in output
        assert "backlog" in output

    def test_history_no_entries(self, tmp_path, monkeypatch, capsys):
        """Test history command when task has no history."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=1
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", all=False)

        monkeypatch.chdir(tmp_path)
        cmd_history(args)

        captured = capsys.readouterr()
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "No history" in output

    def test_history_all_mode(self, tmp_path, monkeypatch, capsys):
        """Test history command in --all mode."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create multiple tasks with history
        for i in range(3):
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1
            )
            task.history.append(HistoryEntry(
                timestamp=utc_now(),
                action="create",
                from_status=None,
                to_status="stub",
                reason=None
            ))
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace(task_id=None, all=True)

        monkeypatch.chdir(tmp_path)
        cmd_history(args)

        captured = capsys.readouterr()
        output = re.sub(r'\x1b\[[0-9;]*m', '', captured.out)
        assert "TEST-00" in output
        assert "TEST-01" in output
        assert "TEST-02" in output
        assert "3" in output and "tasks" in output


class TestStatsCommand:
    """Test cmd_stats functionality."""

    def test_stats_all_tasks(self, tmp_path, monkeypatch, capsys):
        """Test stats command for all tasks."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks in various statuses
        statuses = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.ACTIVE, TaskStatus.DONE]
        for i, status in enumerate(statuses):
            task = Task(
                id=f"TEST-{i:02d}",
                epic="TEST",
                number=i,
                title=f"Task {i}",
                status=status,
                priority=Priority.MEDIUM,
                story_points=2
            )
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace(epic=None, milestone=None)

        monkeypatch.chdir(tmp_path)
        cmd_stats(args)

        captured = capsys.readouterr()
        assert "Total Tasks: 4" in captured.out
        assert "Total Story Points: 8" in captured.out
        assert "stub" in captured.out
        assert "backlog" in captured.out
        assert "active" in captured.out
        assert "done" in captured.out

    def test_stats_filter_by_epic(self, tmp_path, monkeypatch, capsys):
        """Test stats command filtered by epic."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create tasks in different epics
        for i in range(2):
            task = Task(
                id=f"FEAT-{i:02d}",
                epic="FEAT",
                number=i,
                title=f"Feature {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=3
            )
            storage.write_task_file(task)

        for i in range(3):
            task = Task(
                id=f"BUGS-{i:02d}",
                epic="BUGS",
                number=i,
                title=f"Bug {i}",
                status=TaskStatus.ACTIVE,
                priority=Priority.HIGH,
                story_points=1
            )
            storage.write_task_file(task)

        storage.rebuild_manifest()

        args = Namespace(epic="FEAT", milestone=None)

        monkeypatch.chdir(tmp_path)
        cmd_stats(args)

        captured = capsys.readouterr()
        assert "Epic: FEAT" in captured.out
        assert "Total Tasks: 2" in captured.out
        assert "Total Story Points: 6" in captured.out

    def test_stats_empty_project(self, tmp_path, monkeypatch, capsys):
        """Test stats command with no tasks."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        args = Namespace(epic=None, milestone=None)

        monkeypatch.chdir(tmp_path)
        cmd_stats(args)

        captured = capsys.readouterr()
        assert "Total Tasks: 0" in captured.out
        assert "Total Story Points: 0" in captured.out
