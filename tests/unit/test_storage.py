"""
Unit tests for TaskPy storage layer.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.storage import TaskStorage, StorageError, MANIFEST_HEADERS

# Epic and NFR models were removed in REF-08 migration
# Tests for load_epics/load_nfrs are now obsolete and skipped
SKIP_REASON = "Epic and NFR models removed in REF-08 migration - now handled by modern modules"


class TestTaskStorage:
    """Tests for TaskStorage."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def storage(self, temp_dir):
        """Create TaskStorage instance."""
        return TaskStorage(temp_dir)

    def test_is_initialized_false(self, storage):
        """Test is_initialized on fresh directory."""
        assert not storage.is_initialized()

    def test_initialize(self, storage):
        """Test initializing kanban structure."""
        storage.initialize()
        assert storage.is_initialized()
        assert storage.kanban.exists()
        assert storage.info_dir.exists()
        assert storage.status_dir.exists()
        assert storage.manifest_file.exists()

    def test_initialize_creates_status_dirs(self, storage):
        """Test that all status directories are created."""
        storage.initialize()
        for status in TaskStatus:
            status_dir = storage.status_dir / status.value
            assert status_dir.exists()

    def test_initialize_creates_default_configs(self, storage):
        """Test that default configs are created."""
        storage.initialize()
        assert (storage.info_dir / "epics.toml").exists()
        assert (storage.info_dir / "nfrs.toml").exists()
        assert (storage.info_dir / "config.toml").exists()

    def test_initialize_force(self, storage):
        """Test force reinitialize."""
        storage.initialize()
        # Should not raise error with force
        storage.initialize(force=True)

    def test_initialize_already_initialized(self, storage):
        """Test initializing when already initialized."""
        storage.initialize()
        with pytest.raises(StorageError):
            storage.initialize(force=False)

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_load_epics(self, storage):
        """Test loading epic definitions."""
        storage.initialize()
        epics = storage.load_epics()
        assert "BUGS" in epics
        assert "DOCS" in epics
        assert "FEAT" in epics
        assert epics["BUGS"].description == "Bug fixes and corrections"

    @pytest.mark.skip(reason=SKIP_REASON)
    def test_load_nfrs(self, storage):
        """Test loading NFR definitions."""
        storage.initialize()
        nfrs = storage.load_nfrs()
        assert "NFR-SEC-001" in nfrs
        assert "NFR-TEST-001" in nfrs
        assert nfrs["NFR-SEC-001"].default is True

    def test_get_next_task_number_empty(self, storage):
        """Test getting next task number when no tasks exist."""
        storage.initialize()
        number = storage.get_next_task_number("FEAT")
        assert number == 1

    def test_write_and_read_task(self, storage):
        """Test writing and reading a task."""
        storage.initialize()

        task = Task(
            id="FEAT-001",
            title="Test Feature",
            epic="FEAT",
            number=1,
            status=TaskStatus.BACKLOG,
            story_points=5,
            priority=Priority.HIGH
        )

        storage.write_task_file(task)

        # Read back
        path = storage.get_task_path("FEAT-001", TaskStatus.BACKLOG)
        assert path.exists()

        read_task = storage.read_task_file(path)
        assert read_task.id == "FEAT-001"
        assert read_task.title == "Test Feature"
        assert read_task.story_points == 5

    def test_find_task_file(self, storage):
        """Test finding a task file across status directories."""
        storage.initialize()

        task = Task(
            id="BUGS-001",
            title="Fix bug",
            epic="BUGS",
            number=1,
            status=TaskStatus.ACTIVE
        )

        storage.write_task_file(task)

        result = storage.find_task_file("BUGS-001")
        assert result is not None
        path, status = result
        assert status == TaskStatus.ACTIVE
        assert path.exists()

    def test_find_task_file_not_found(self, storage):
        """Test finding non-existent task."""
        storage.initialize()
        result = storage.find_task_file("NOTFOUND-999")
        assert result is None

    def test_manifest_updates(self, storage):
        """Test that manifest is updated when task is written."""
        storage.initialize()

        task = Task(
            id="DOCS-001",
            title="Write docs",
            epic="DOCS",
            number=1
        )

        storage.write_task_file(task)

        # Check manifest
        content = storage.manifest_file.read_text()
        assert "DOCS-001" in content
        assert "Write docs" in content

    def test_gitignore_updated(self, storage, temp_dir):
        """Test that .gitignore is updated."""
        storage.initialize()

        gitignore = temp_dir / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "data/kanban" in content

    def test_rebuild_manifest_from_existing_files(self, storage):
        """Rebuild manifest should index existing task files."""
        storage.initialize()

        task = Task(
            id="FEAT-001",
            title="Existing task",
            epic="FEAT",
            number=1,
            status=TaskStatus.STUB,
            story_points=3,
            priority=Priority.MEDIUM,
        )

        storage.write_task_file(task)

        # Simulate missing entries by truncating manifest to header only
        header_line = "\t".join(MANIFEST_HEADERS)
        storage.manifest_file.write_text(f"{header_line}\n")

        rebuilt = storage.rebuild_manifest()
        assert rebuilt == 1

        manifest_rows = storage.manifest_file.read_text().splitlines()
        assert len(manifest_rows) == 2
        assert "FEAT-001" in manifest_rows[1]
