"""
Integration tests for TaskPy CLI.
"""

import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path


class TestCLI:
    """Integration tests for CLI commands."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp = Path(tempfile.mkdtemp())
        yield temp
        shutil.rmtree(temp)

    def run_taskpy(self, args, cwd=None):
        """Run taskpy command."""
        cmd = ["taskpy"] + args
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return result

    def test_version(self):
        """Test taskpy --version."""
        result = self.run_taskpy(["--version"])
        assert result.returncode == 0
        # Version output includes logo which may have styling
        assert "Version:" in result.stdout
        assert "0.1.0" in result.stdout

    def test_init(self, temp_dir):
        """Test taskpy init."""
        result = self.run_taskpy(["init"], cwd=temp_dir)
        assert result.returncode == 0
        assert (temp_dir / "data" / "kanban").exists()
        assert (temp_dir / "data" / "kanban" / "manifest.tsv").exists()

    def test_create_task(self, temp_dir):
        """Test creating a task."""
        # Init first
        self.run_taskpy(["init"], cwd=temp_dir)

        # Create task with data mode to avoid ANSI codes
        result = self.run_taskpy(
            ["--view=data", "create", "FEAT", "Test Feature", "--sp", "5", "--priority", "high"],
            cwd=temp_dir
        )
        assert result.returncode == 0
        assert "FEAT-001" in result.stdout

        # Check file exists
        task_file = temp_dir / "data" / "kanban" / "status" / "backlog" / "FEAT-001.md"
        assert task_file.exists()

    def test_list_tasks(self, temp_dir):
        """Test listing tasks."""
        # Init and create task
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "BUGS", "Fix bug"], cwd=temp_dir)

        # List
        result = self.run_taskpy(["list"], cwd=temp_dir)
        assert result.returncode == 0
        assert "BUGS-001" in result.stdout

    def test_show_task(self, temp_dir):
        """Test showing a task."""
        # Init and create
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["--view=data", "create", "DOCS", "Write docs"], cwd=temp_dir)

        # Show with data mode
        result = self.run_taskpy(["--view=data", "show", "DOCS-001"], cwd=temp_dir)
        assert result.returncode == 0
        assert "DOCS-001" in result.stdout
        assert "Write docs" in result.stdout

    def test_promote_task(self, temp_dir):
        """Test promoting a task."""
        # Init and create
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature"], cwd=temp_dir)

        # Promote
        result = self.run_taskpy(["promote", "FEAT-001"], cwd=temp_dir)
        assert result.returncode == 0

        # Check it moved
        ready_file = temp_dir / "data" / "kanban" / "status" / "ready" / "FEAT-001.md"
        assert ready_file.exists()

    def test_stats(self, temp_dir):
        """Test stats command."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1", "--sp", "5"], cwd=temp_dir)
        self.run_taskpy(["create", "BUGS", "Bug 1", "--sp", "2"], cwd=temp_dir)

        # Stats
        result = self.run_taskpy(["stats"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Total Tasks: 2" in result.stdout
        assert "Total Story Points: 7" in result.stdout

    def test_epics(self, temp_dir):
        """Test epics command."""
        # Init
        self.run_taskpy(["init"], cwd=temp_dir)

        # List epics
        result = self.run_taskpy(["epics"], cwd=temp_dir)
        assert result.returncode == 0
        assert "BUGS" in result.stdout
        assert "FEAT" in result.stdout
        assert "DOCS" in result.stdout

    def test_data_mode(self, temp_dir):
        """Test --view=data mode."""
        # Init and create
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature"], cwd=temp_dir)

        # List in data mode
        result = self.run_taskpy(["--view=data", "list", "--format", "ids"], cwd=temp_dir)
        assert result.returncode == 0
        assert "FEAT-001" in result.stdout
        # Should not have ANSI color codes
        assert "[38;5;" not in result.stdout
