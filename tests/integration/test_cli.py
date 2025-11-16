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
        assert "FEAT-01" in result.stdout

        # Check file exists (created in stub by default)
        task_file = temp_dir / "data" / "kanban" / "status" / "stub" / "FEAT-01.md"
        assert task_file.exists()

    def test_list_tasks(self, temp_dir):
        """Test listing tasks."""
        # Init and create task
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "BUGS", "Fix bug"], cwd=temp_dir)

        # List
        result = self.run_taskpy(["list"], cwd=temp_dir)
        assert result.returncode == 0
        assert "BUGS-01" in result.stdout

    def test_show_task(self, temp_dir):
        """Test showing a task."""
        # Init and create
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["--view=data", "create", "DOCS", "Write docs"], cwd=temp_dir)

        # Show with data mode
        result = self.run_taskpy(["--view=data", "show", "DOCS-01"], cwd=temp_dir)
        assert result.returncode == 0
        assert "DOCS-01" in result.stdout
        assert "Write docs" in result.stdout

    def test_promote_task(self, temp_dir):
        """Test promoting a task."""
        # Init and create (starts in stub)
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature"], cwd=temp_dir)

        # Promote stub → backlog
        result = self.run_taskpy(["promote", "FEAT-01"], cwd=temp_dir)
        assert result.returncode == 0

        # Promote backlog → ready
        result = self.run_taskpy(["promote", "FEAT-01"], cwd=temp_dir)
        assert result.returncode == 0

        # Check it moved to ready
        ready_file = temp_dir / "data" / "kanban" / "status" / "ready" / "FEAT-01.md"
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
        assert "FEAT-01" in result.stdout
        # Should not have ANSI color codes
        assert "[38;5;" not in result.stdout

    def test_milestones_list(self, temp_dir):
        """Test listing milestones."""
        # Init
        self.run_taskpy(["init"], cwd=temp_dir)

        # List milestones
        result = self.run_taskpy(["milestones"], cwd=temp_dir)
        assert result.returncode == 0
        assert "milestone-1" in result.stdout
        assert "milestone-2" in result.stdout
        assert "milestone-3" in result.stdout
        assert "Foundation MVP" in result.stdout

    def test_milestone_show(self, temp_dir):
        """Test showing milestone details."""
        # Init
        self.run_taskpy(["init"], cwd=temp_dir)

        # Show milestone
        result = self.run_taskpy(["milestone", "show", "milestone-1"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Foundation MVP" in result.stdout
        assert "Priority: 1" in result.stdout
        assert "Total Tasks: 0" in result.stdout

    def test_milestone_assign(self, temp_dir):
        """Test assigning task to milestone."""
        # Init and create task
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature"], cwd=temp_dir)

        # Assign to milestone
        result = self.run_taskpy(["milestone", "assign", "FEAT-01", "milestone-1"], cwd=temp_dir)
        assert result.returncode == 0

        # Verify assignment
        result = self.run_taskpy(["milestone", "show", "milestone-1"], cwd=temp_dir)
        assert "Total Tasks: 1" in result.stdout

    def test_milestone_start(self, temp_dir):
        """Test starting a milestone."""
        # Init
        self.run_taskpy(["init"], cwd=temp_dir)

        # Start milestone-2 (milestone-1 is already active)
        result = self.run_taskpy(["milestone", "start", "milestone-2"], cwd=temp_dir)
        assert result.returncode == 0

        # Verify it's active
        result = self.run_taskpy(["milestones"], cwd=temp_dir)
        # Both should show active status (🟢)
        assert result.returncode == 0

    def test_create_with_milestone(self, temp_dir):
        """Test creating task with milestone assignment."""
        # Init
        self.run_taskpy(["init"], cwd=temp_dir)

        # Create task with milestone
        result = self.run_taskpy(
            ["--view=data", "create", "FEAT", "Test Feature", "--milestone", "milestone-1"],
            cwd=temp_dir
        )
        assert result.returncode == 0
        assert "FEAT-01" in result.stdout
        assert "Milestone: milestone-1" in result.stdout

    def test_list_filter_by_milestone(self, temp_dir):
        """Test filtering tasks by milestone."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1", "--milestone", "milestone-1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2", "--milestone", "milestone-2"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 3"], cwd=temp_dir)

        # Filter by milestone-1
        result = self.run_taskpy(["list", "--milestone", "milestone-1"], cwd=temp_dir)
        assert result.returncode == 0
        assert "FEAT-01" in result.stdout
        assert "FEAT-02" not in result.stdout
        assert "FEAT-03" not in result.stdout

    def test_stats_filter_by_milestone(self, temp_dir):
        """Test stats with milestone filter."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1", "--sp", "5", "--milestone", "milestone-1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2", "--sp", "3", "--milestone", "milestone-1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 3", "--sp", "2"], cwd=temp_dir)

        # Stats for milestone-1
        result = self.run_taskpy(["stats", "--milestone", "milestone-1"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Total Tasks: 2" in result.stdout
        assert "Total Story Points: 8" in result.stdout

    def test_sprint_add(self, temp_dir):
        """Test adding task to sprint."""
        # Init and create task
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Test Feature"], cwd=temp_dir)

        # Add to sprint
        result = self.run_taskpy(["--view=data", "sprint", "add", "FEAT-01"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Added FEAT-01 to sprint" in result.stdout

        # Verify task is in sprint
        result = self.run_taskpy(["sprint", "list"], cwd=temp_dir)
        assert "FEAT-01" in result.stdout

    def test_sprint_remove(self, temp_dir):
        """Test removing task from sprint."""
        # Init, create, and add to sprint
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Test Feature"], cwd=temp_dir)
        self.run_taskpy(["sprint", "add", "FEAT-01"], cwd=temp_dir)

        # Remove from sprint
        result = self.run_taskpy(["--view=data", "sprint", "remove", "FEAT-01"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Removed FEAT-01 from sprint" in result.stdout

        # Verify task is not in sprint
        result = self.run_taskpy(["--view=data", "sprint", "list"], cwd=temp_dir)
        assert "No tasks in sprint" in result.stdout

    def test_sprint_list(self, temp_dir):
        """Test listing sprint tasks."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2"], cwd=temp_dir)

        # Add tasks to sprint
        self.run_taskpy(["sprint", "add", "FEAT-01"], cwd=temp_dir)
        self.run_taskpy(["sprint", "add", "FEAT-02"], cwd=temp_dir)

        # List sprint tasks
        result = self.run_taskpy(["sprint", "list"], cwd=temp_dir)
        assert result.returncode == 0
        assert "FEAT-01" in result.stdout
        assert "FEAT-02" in result.stdout
        assert "Sprint Tasks (2 found)" in result.stdout

    def test_sprint_clear(self, temp_dir):
        """Test clearing all sprint tasks."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2"], cwd=temp_dir)

        # Add tasks to sprint
        self.run_taskpy(["sprint", "add", "FEAT-01"], cwd=temp_dir)
        self.run_taskpy(["sprint", "add", "FEAT-02"], cwd=temp_dir)

        # Clear sprint
        result = self.run_taskpy(["--view=data", "sprint", "clear"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Cleared 2 tasks from sprint" in result.stdout

        # Verify sprint is empty
        result = self.run_taskpy(["--view=data", "sprint", "list"], cwd=temp_dir)
        assert "No tasks in sprint" in result.stdout

    def test_sprint_stats(self, temp_dir):
        """Test sprint statistics."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1", "--sp", "5"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2", "--sp", "3"], cwd=temp_dir)

        # Add tasks to sprint
        self.run_taskpy(["sprint", "add", "FEAT-01"], cwd=temp_dir)
        self.run_taskpy(["sprint", "add", "FEAT-02"], cwd=temp_dir)

        # Check stats
        result = self.run_taskpy(["sprint", "stats"], cwd=temp_dir)
        assert result.returncode == 0
        assert "Total Tasks: 2" in result.stdout
        assert "Total Story Points: 8" in result.stdout

    def test_list_filter_by_sprint(self, temp_dir):
        """Test list with sprint filter."""
        # Init and create tasks
        self.run_taskpy(["init"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 1"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 2"], cwd=temp_dir)
        self.run_taskpy(["create", "FEAT", "Feature 3"], cwd=temp_dir)

        # Add only FEAT-01 to sprint
        self.run_taskpy(["sprint", "add", "FEAT-01"], cwd=temp_dir)

        # List sprint tasks
        result = self.run_taskpy(["list", "--sprint"], cwd=temp_dir)
        assert result.returncode == 0
        assert "FEAT-01" in result.stdout
        assert "FEAT-02" not in result.stdout
        assert "FEAT-03" not in result.stdout
