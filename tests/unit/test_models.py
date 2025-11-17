"""
Unit tests for TaskPy models.
"""

import pytest
from datetime import datetime
from taskpy.models import (
    Task, Epic, NFR, TaskStatus, Priority,
    TaskReference, Verification, VerificationStatus, utc_now
)


class TestTask:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test creating a basic task."""
        task = Task(
            id="FEAT-001",
            title="Test Feature",
            epic="FEAT",
            number=1,
        )
        assert task.id == "FEAT-001"
        assert task.title == "Test Feature"
        assert task.epic == "FEAT"
        assert task.number == 1
        assert task.status == TaskStatus.BACKLOG
        assert task.story_points == 0
        assert task.priority == Priority.MEDIUM

    def test_parse_task_id(self):
        """Test parsing task IDs."""
        epic, number = Task.parse_task_id("BUGS-042")
        assert epic == "BUGS"
        assert number == 42

    def test_parse_task_id_invalid(self):
        """Test parsing invalid task IDs."""
        with pytest.raises(ValueError):
            Task.parse_task_id("invalid")
        with pytest.raises(ValueError):
            Task.parse_task_id("BUGS")
        with pytest.raises(ValueError):
            Task.parse_task_id("BUGS-")

    def test_make_task_id(self):
        """Test generating task IDs."""
        # Test 2-digit format for numbers <= 99
        task_id = Task.make_task_id("DOCS", 5)
        assert task_id == "DOCS-05"

        # Test 3-digit format for numbers >= 100
        task_id = Task.make_task_id("BUGS", 100)
        assert task_id == "BUGS-100"

        # Test boundary case
        task_id = Task.make_task_id("FEAT", 99)
        assert task_id == "FEAT-99"

    def test_task_filename(self):
        """Test task filename generation."""
        task = Task(id="REF-010", title="Refactor", epic="REF", number=10)
        assert task.filename == "REF-010.md"

    def test_task_epic_prefix(self):
        """Test epic prefix extraction."""
        task = Task(id="UAT-003", title="Test", epic="UAT", number=3)
        assert task.epic_prefix == "UAT"

    def test_task_to_manifest_row(self):
        """Test converting task to manifest row."""
        task = Task(
            id="BUGS-001",
            title="Fix bug",
            epic="BUGS",
            number=1,
            status=TaskStatus.ACTIVE,
            story_points=3,
            priority=Priority.HIGH,
            tags=["critical", "security"]
        )
        row = task.to_manifest_row()
        assert row[0] == "BUGS-001"
        assert row[1] == "BUGS"
        assert row[2] == "1"
        assert row[3] == "active"
        assert row[4] == "Fix bug"
        assert row[5] == "3"
        assert row[6] == "high"
        assert "critical" in row[9]
        assert "security" in row[9]


class TestEpic:
    """Tests for Epic model."""

    def test_epic_creation(self):
        """Test creating an epic."""
        epic = Epic(
            name="CUSTOM",
            description="Custom work",
            active=True
        )
        assert epic.name == "CUSTOM"
        assert epic.description == "Custom work"
        assert epic.active is True
        assert epic.task_prefix == "CUSTOM"

    def test_epic_with_custom_prefix(self):
        """Test epic with custom prefix."""
        epic = Epic(
            name="RESEARCH",
            description="Research work",
            prefix="RX"
        )
        assert epic.task_prefix == "RX"

    def test_epic_to_dict(self):
        """Test converting epic to dict."""
        epic = Epic(
            name="FEAT",
            description="Features",
            story_point_budget=100
        )
        d = epic.to_dict()
        assert d["description"] == "Features"
        assert d["story_point_budget"] == 100


class TestNFR:
    """Tests for NFR model."""

    def test_nfr_creation(self):
        """Test creating an NFR."""
        nfr = NFR(
            id="NFR-SEC-001",
            category="SEC",
            number=1,
            title="Security requirement",
            description="Must be secure",
            default=True
        )
        assert nfr.id == "NFR-SEC-001"
        assert nfr.category == "SEC"
        assert nfr.number == 1
        assert nfr.default is True

    def test_nfr_to_dict(self):
        """Test converting NFR to dict."""
        nfr = NFR(
            id="NFR-TEST-001",
            category="TEST",
            number=1,
            title="Testing",
            description="Must have tests",
            verification="Run tests"
        )
        d = nfr.to_dict()
        assert d["title"] == "Testing"
        assert d["verification"] == "Run tests"


class TestTaskReference:
    """Tests for TaskReference model."""

    def test_task_reference_creation(self):
        """Test creating task references."""
        ref = TaskReference(
            code=["src/main.rs", "src/lib.rs"],
            docs=["README.md"],
            tests=["tests/integration_test.rs"]
        )
        assert len(ref.code) == 2
        assert len(ref.docs) == 1
        assert len(ref.tests) == 1
        assert len(ref.plans) == 0


class TestVerification:
    """Tests for Verification model."""

    def test_verification_creation(self):
        """Test creating verification."""
        verif = Verification(
            command="cargo test",
            status=VerificationStatus.PENDING
        )
        assert verif.command == "cargo test"
        assert verif.status == VerificationStatus.PENDING
        assert verif.last_run is None

    def test_verification_to_dict(self):
        """Test converting verification to dict."""
        now = utc_now()
        verif = Verification(
            command="pytest",
            status=VerificationStatus.PASSED,
            last_run=now
        )
        d = verif.to_dict()
        assert d["command"] == "pytest"
        assert d["status"] == "passed"
        assert "last_run" in d
