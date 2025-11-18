"""
Unit tests for modern workflow module commands.

Tests the 3 workflow commands: promote, demote, move.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from argparse import Namespace

from taskpy.modern.workflow.commands import (
    cmd_promote,
    cmd_demote,
    cmd_move,
    validate_promotion,
    validate_done_demotion,
    validate_stub_to_backlog,
    validate_active_to_qa,
    validate_qa_to_done,
    parse_task_ids,
    log_override,
)
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority, VerificationStatus


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_task_ids_space_separated(self):
        """Test parsing space-separated task IDs."""
        result = parse_task_ids(["FEAT-01", "BUGS-02", "TEST-03"])
        assert result == ["FEAT-01", "BUGS-02", "TEST-03"]

    def test_parse_task_ids_comma_separated(self):
        """Test parsing comma-separated task IDs."""
        result = parse_task_ids(["FEAT-01,BUGS-02,TEST-03"])
        assert result == ["FEAT-01", "BUGS-02", "TEST-03"]

    def test_parse_task_ids_mixed(self):
        """Test parsing mixed format task IDs."""
        result = parse_task_ids(["FEAT-01,BUGS-02", "TEST-03"])
        assert result == ["FEAT-01", "BUGS-02", "TEST-03"]

    def test_parse_task_ids_with_spaces(self):
        """Test parsing task IDs with spaces around commas."""
        result = parse_task_ids(["FEAT-01, BUGS-02 , TEST-03"])
        assert result == ["FEAT-01", "BUGS-02", "TEST-03"]

    def test_parse_task_ids_lowercase_normalized(self):
        """Test that lowercase IDs are normalized to uppercase."""
        result = parse_task_ids(["feat-01", "bugs-02"])
        assert result == ["FEAT-01", "BUGS-02"]

    def test_parse_task_ids_deduplicates(self):
        """Test that duplicates are removed."""
        result = parse_task_ids(["FEAT-01", "FEAT-01", "BUGS-02"])
        assert result == ["FEAT-01", "BUGS-02"]

    def test_log_override(self, tmp_path):
        """Test logging override to task history (REF-03)."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        # Create a task first
        from taskpy.legacy.models import Task, TaskStatus
        task = Task(
            id="TEST-01",
            title="Test Task",
            epic="TEST",
            number=1,
            status=TaskStatus.ACTIVE,
            story_points=2
        )
        storage.write_task_file(task)

        # Log override
        updated_task = log_override(storage, "TEST-01", "active", "qa", "Testing override")

        # Verify override was added to task history
        assert updated_task is not None
        assert len(updated_task.history) == 1
        assert updated_task.history[0].action == "override"
        assert updated_task.history[0].from_status == "active"
        assert updated_task.history[0].to_status == "qa"
        assert updated_task.history[0].reason == "Testing override"


class TestValidationFunctions:
    """Test gate validation functions."""

    def test_validate_stub_to_backlog_success(self):
        """Test successful stub→backlog validation."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=3,
            content="This is a detailed description with enough content to pass validation"
        )

        is_valid, blockers = validate_stub_to_backlog(task)
        assert is_valid is True
        assert len(blockers) == 0

    def test_validate_stub_to_backlog_missing_description(self):
        """Test stub→backlog validation with missing description."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=3,
            content="Short"
        )

        is_valid, blockers = validate_stub_to_backlog(task)
        assert is_valid is False
        assert any("description" in b for b in blockers)

    def test_validate_stub_to_backlog_missing_story_points(self):
        """Test stub→backlog validation with missing story points."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=0,
            content="This is a detailed description with enough content"
        )

        is_valid, blockers = validate_stub_to_backlog(task)
        assert is_valid is False
        assert any("story points" in b for b in blockers)

    def test_validate_active_to_qa_success(self):
        """Test successful active→qa validation."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.ACTIVE,
            priority=Priority.MEDIUM,
            story_points=3
        )
        task.references.code.append("src/test.py")
        task.references.tests.append("tests/test_test.py")
        task.verification.command = "pytest tests/test_test.py"
        task.verification.status = VerificationStatus.PASSED

        is_valid, blockers = validate_active_to_qa(task)
        assert is_valid is True
        assert len(blockers) == 0

    def test_validate_active_to_qa_missing_code_refs(self):
        """Test active→qa validation with missing code references."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.ACTIVE,
            priority=Priority.MEDIUM,
            story_points=3
        )

        is_valid, blockers = validate_active_to_qa(task)
        assert is_valid is False
        assert any("code or doc references" in b for b in blockers)

    def test_validate_active_to_qa_docs_task(self):
        """Test active→qa validation for DOCS task."""
        task = Task(
            id="DOCS-01",
            epic="DOCS",
            number=1,
            title="Documentation task",
            status=TaskStatus.ACTIVE,
            priority=Priority.MEDIUM,
            story_points=2
        )
        task.references.docs.append("README.md")

        is_valid, blockers = validate_active_to_qa(task)
        assert is_valid is True
        assert len(blockers) == 0

    def test_validate_qa_to_done_success(self):
        """Test successful qa→done validation."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.QA,
            priority=Priority.MEDIUM,
            story_points=3,
            commit_hash="abc123"
        )

        is_valid, blockers = validate_qa_to_done(task)
        assert is_valid is True
        assert len(blockers) == 0

    def test_validate_qa_to_done_missing_commit(self):
        """Test qa→done validation with missing commit hash."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.QA,
            priority=Priority.MEDIUM,
            story_points=3
        )

        is_valid, blockers = validate_qa_to_done(task)
        assert is_valid is False
        assert any("commit hash" in b for b in blockers)

    def test_validate_done_demotion_success(self):
        """Test successful done demotion validation."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.DONE,
            priority=Priority.MEDIUM,
            story_points=3
        )

        is_valid, blockers = validate_done_demotion(task, "Found a bug")
        assert is_valid is True
        assert len(blockers) == 0

    def test_validate_done_demotion_missing_reason(self):
        """Test done demotion validation with missing reason."""
        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.DONE,
            priority=Priority.MEDIUM,
            story_points=3
        )

        is_valid, blockers = validate_done_demotion(task, None)
        assert is_valid is False
        assert any("reason" in b for b in blockers)

    def test_validate_promotion_blocked_task(self):
        """Test that blocked tasks cannot be promoted."""
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

        is_valid, blockers = validate_promotion(task, TaskStatus.ACTIVE)
        assert is_valid is False
        assert any("blocked" in b.lower() for b in blockers)


class TestPromoteCommand:
    """Test cmd_promote functionality."""

    def test_promote_stub_to_backlog(self, tmp_path, monkeypatch):
        """Test promoting from stub to backlog."""
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
            content="This is a detailed description with enough content to pass validation"
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", target_status=None, commit=None, override=False)

        monkeypatch.chdir(tmp_path)
        cmd_promote(args)

        # Verify task was promoted
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.BACKLOG

        updated_task = storage.read_task_file(path)
        assert updated_task.status == TaskStatus.BACKLOG
        assert len(updated_task.history) > 0
        assert updated_task.history[-1].action == "promote"

    def test_promote_with_target_status(self, tmp_path, monkeypatch):
        """Test promoting with explicit target status."""
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
            content="Detailed description"
        )
        storage.write_task_file(task)

        args = Namespace(
            task_id="TEST-01",
            target_status="ready",
            commit=None,
            override=True,
            reason="Skip backlog for urgent work"
        )

        monkeypatch.chdir(tmp_path)
        cmd_promote(args)

        # Verify task went directly to ready
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.READY

    def test_promote_regression_to_qa(self, tmp_path, monkeypatch):
        """Test promoting from regression back to QA."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.REGRESSION,
            priority=Priority.MEDIUM,
            story_points=3
        )
        task.references.code.append("src/test.py")
        task.references.tests.append("tests/test_test.py")
        task.verification.command = "pytest"
        task.verification.status = VerificationStatus.PASSED

        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", target_status=None, commit=None, override=False)

        monkeypatch.chdir(tmp_path)
        cmd_promote(args)

        # Verify task went to QA
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.QA

    def test_promote_with_override(self, tmp_path, monkeypatch):
        """Test promoting with override flag."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=0,  # Missing story points - would normally fail
            content="Short"  # Too short - would normally fail
        )
        storage.write_task_file(task)

        args = Namespace(
            task_id="TEST-01",
            target_status=None,
            commit=None,
            override=True,
            reason="Emergency hotfix"
        )

        monkeypatch.chdir(tmp_path)
        cmd_promote(args)

        # Verify task was promoted despite validation failures
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.BACKLOG

        # Check override was logged to task history (REF-03)
        task = storage.read_task_file(path)
        assert len(task.history) >= 1

        # Should have both override and promote entries
        override_entries = [h for h in task.history if h.action == "override"]
        assert len(override_entries) == 1
        assert override_entries[0].reason == "Emergency hotfix"
        assert override_entries[0].from_status == "stub"
        assert override_entries[0].to_status == "backlog"


class TestDemoteCommand:
    """Test cmd_demote functionality."""

    def test_demote_qa_to_regression(self, tmp_path, monkeypatch):
        """Test demoting from QA to regression."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.QA,
            priority=Priority.MEDIUM,
            story_points=3
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", to=None, reason=None, override=False)

        monkeypatch.chdir(tmp_path)
        cmd_demote(args)

        # Verify task went to regression
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.REGRESSION

        updated_task = storage.read_task_file(path)
        assert updated_task.status == TaskStatus.REGRESSION
        assert len(updated_task.history) > 0
        assert updated_task.history[-1].action == "demote"

    def test_demote_regression_to_active(self, tmp_path, monkeypatch):
        """Test demoting from regression to active."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.REGRESSION,
            priority=Priority.MEDIUM,
            story_points=3
        )
        storage.write_task_file(task)

        args = Namespace(task_id="TEST-01", to=None, reason=None, override=False)

        monkeypatch.chdir(tmp_path)
        cmd_demote(args)

        # Verify task went to active
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.ACTIVE

    def test_demote_from_done_requires_reason(self, tmp_path, monkeypatch):
        """Test that demoting from done requires a reason."""
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

        args = Namespace(task_id="TEST-01", to=None, reason="Found critical bug", override=False)

        monkeypatch.chdir(tmp_path)
        cmd_demote(args)

        # Verify task was demoted
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        # Should go back one step in workflow
        assert status == TaskStatus.QA

        updated_task = storage.read_task_file(path)
        assert updated_task.demotion_reason == "Found critical bug"


class TestMoveCommand:
    """Test cmd_move functionality."""

    def test_move_single_task(self, tmp_path, monkeypatch):
        """Test moving a single task."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        task = Task(
            id="TEST-01",
            epic="TEST",
            number=1,
            title="Test task",
            status=TaskStatus.STUB,
            priority=Priority.MEDIUM,
            story_points=3
        )
        storage.write_task_file(task)

        args = Namespace(
            task_ids=["TEST-01"],
            status="blocked",
            reason="Waiting on external dependency"
        )

        monkeypatch.chdir(tmp_path)
        cmd_move(args)

        # Verify task was moved
        result = storage.find_task_file("TEST-01")
        assert result is not None
        path, status = result
        assert status == TaskStatus.BLOCKED

        updated_task = storage.read_task_file(path)
        assert updated_task.history[-1].reason == "Waiting on external dependency"

    def test_move_multiple_tasks_space_separated(self, tmp_path, monkeypatch):
        """Test moving multiple tasks (space-separated)."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        for i in range(1, 4):
            task = Task(
                id=f"TEST-0{i}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.STUB,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        args = Namespace(
            task_ids=["TEST-01", "TEST-02", "TEST-03"],
            status="backlog",
            reason="Batch grooming"
        )

        monkeypatch.chdir(tmp_path)
        cmd_move(args)

        # Verify all tasks were moved
        for i in range(1, 4):
            result = storage.find_task_file(f"TEST-0{i}")
            assert result is not None
            path, status = result
            assert status == TaskStatus.BACKLOG

    def test_move_multiple_tasks_comma_separated(self, tmp_path, monkeypatch):
        """Test moving multiple tasks (comma-separated)."""
        storage = TaskStorage(tmp_path)
        storage.initialize()

        for i in range(1, 4):
            task = Task(
                id=f"TEST-0{i}",
                epic="TEST",
                number=i,
                title=f"Test task {i}",
                status=TaskStatus.BACKLOG,
                priority=Priority.MEDIUM,
                story_points=1
            )
            storage.write_task_file(task)

        args = Namespace(
            task_ids=["TEST-01,TEST-02,TEST-03"],
            status="ready",
            reason="Ready for development"
        )

        monkeypatch.chdir(tmp_path)
        cmd_move(args)

        # Verify all tasks were moved
        for i in range(1, 4):
            result = storage.find_task_file(f"TEST-0{i}")
            assert result is not None
            path, status = result
            assert status == TaskStatus.READY
