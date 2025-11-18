"""
Unit tests for modern views output module.

Tests boxy/rolo integration and output mode handling.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from taskpy.modern.views.output import (
    OutputMode,
    Theme,
    has_boxy,
    has_rolo,
    dim,
    rolo_table,
    show_card,
    show_column,
)


class TestOutputMode:
    """Test OutputMode enum."""

    def test_output_modes_exist(self):
        """Test that all expected output modes are defined."""
        assert OutputMode.PRETTY.value == "pretty"
        assert OutputMode.DATA.value == "data"
        assert OutputMode.AGENT.value == "agent"


class TestTheme:
    """Test Theme enum."""

    def test_themes_exist(self):
        """Test that all expected themes are defined."""
        assert Theme.SUCCESS.value == "success"
        assert Theme.WARNING.value == "warning"
        assert Theme.ERROR.value == "error"
        assert Theme.INFO.value == "info"
        assert Theme.MAGIC.value == "magic"
        assert Theme.TASK.value == "task"
        assert Theme.PLAIN.value == "plain"


class TestBoxyAvailability:
    """Test boxy availability detection."""

    @patch('taskpy.modern.views.output.shutil.which')
    def test_boxy_not_in_path(self, mock_which):
        """Test boxy detection when not in PATH."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._BOXY_AVAILABLE = None

        mock_which.return_value = None
        assert has_boxy() is False

    @patch.dict('os.environ', {'REPOS_USE_BOXY': '1'})
    def test_boxy_disabled_by_env(self):
        """Test boxy disabled via environment variable."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._BOXY_AVAILABLE = None

        assert has_boxy() is False

    @patch('taskpy.modern.views.output.subprocess.run')
    @patch('taskpy.modern.views.output.shutil.which')
    def test_boxy_available(self, mock_which, mock_run):
        """Test boxy detection when available."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._BOXY_AVAILABLE = None

        mock_which.return_value = "/usr/bin/boxy"
        mock_run.return_value = MagicMock(returncode=0)

        assert has_boxy() is True

    @patch('taskpy.modern.views.output.subprocess.run')
    @patch('taskpy.modern.views.output.shutil.which')
    def test_boxy_check_caching(self, mock_which, mock_run):
        """Test that boxy availability is cached."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._BOXY_AVAILABLE = None

        mock_which.return_value = "/usr/bin/boxy"
        mock_run.return_value = MagicMock(returncode=0)

        # First call
        has_boxy()
        # Second call should use cache
        has_boxy()

        # Should only call subprocess once due to caching
        assert mock_run.call_count == 1


class TestRoloAvailability:
    """Test rolo availability detection."""

    @patch('taskpy.modern.views.output.shutil.which')
    def test_rolo_not_in_path(self, mock_which):
        """Test rolo detection when not in PATH."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._ROLO_AVAILABLE = None

        mock_which.return_value = None
        assert has_rolo() is False

    @patch('taskpy.modern.views.output.subprocess.run')
    @patch('taskpy.modern.views.output.shutil.which')
    def test_rolo_available(self, mock_which, mock_run):
        """Test rolo detection when available."""
        # Reset cache
        import taskpy.modern.views.output
        taskpy.modern.views.output._ROLO_AVAILABLE = None

        mock_which.return_value = "/usr/bin/rolo"
        mock_run.return_value = MagicMock(returncode=0)

        assert has_rolo() is True


class TestDim:
    """Test dim text styling."""

    def test_dim_wraps_text_in_ansi(self):
        """Test that dim applies ANSI dim codes."""
        result = dim("test")
        assert result == "\033[2mtest\033[0m"


class TestRoloTable:
    """Test rolo table rendering."""

    @patch('taskpy.modern.views.output.has_rolo')
    def test_rolo_table_data_mode(self, mock_rolo, capsys):
        """Test rolo_table in DATA mode uses plain fallback."""
        headers = ["ID", "Title"]
        rows = [["TASK-1", "Test task"]]

        rolo_table(headers, rows, output_mode=OutputMode.DATA)

        captured = capsys.readouterr()
        assert "ID" in captured.out
        assert "TASK-1" in captured.out

    @patch('taskpy.modern.views.output.has_rolo')
    def test_rolo_table_fallback_when_unavailable(self, mock_rolo, capsys):
        """Test rolo_table falls back to plain when rolo unavailable."""
        mock_rolo.return_value = False

        headers = ["ID", "Title"]
        rows = [["TASK-1", "Test task"]]

        result = rolo_table(headers, rows, output_mode=OutputMode.PRETTY)

        assert result is False  # Returns False when using fallback
        captured = capsys.readouterr()
        assert "ID" in captured.out


class TestShowCard:
    """Test task card display."""

    @patch('taskpy.modern.views.output.has_boxy')
    def test_show_card_data_mode(self, mock_boxy, capsys):
        """Test show_card in DATA mode."""
        task = {
            'id': 'TASK-1',
            'title': 'Test task',
            'status': 'active',
        }

        show_card(task, output_mode=OutputMode.DATA)

        captured = capsys.readouterr()
        assert "ID: TASK-1" in captured.out
        assert "Title: Test task" in captured.out
        assert "Status: active" in captured.out

    def test_show_card_agent_mode(self, capsys):
        """Test show_card in AGENT mode prints JSON."""
        task = {
            'id': 'TASK-1',
            'title': 'Test task',
            'status': 'active',
            'priority': 'high',
            'story_points': 5,
        }

        show_card(task, output_mode=OutputMode.AGENT)
        payload = json.loads(capsys.readouterr().out)
        assert payload["id"] == "TASK-1"
        assert payload["priority"] == "high"


class TestShowColumn:
    """Test kanban column display."""

    @patch('taskpy.modern.views.output.has_boxy')
    def test_show_column_data_mode(self, mock_boxy, capsys):
        """Test show_column in DATA mode."""
        tasks = [
            {'id': 'TASK-1', 'title': 'First', 'story_points': 3, 'in_sprint': 'true'},
            {'id': 'TASK-2', 'title': 'Second', 'story_points': 5, 'in_sprint': 'false'},
        ]

        show_column("backlog", tasks, output_mode=OutputMode.DATA)

        captured = capsys.readouterr()
        assert "BACKLOG (2 tasks)" in captured.out

    def test_show_column_agent_mode(self, capsys):
        """Test show_column emits JSON in agent mode."""
        tasks = [
            {'id': 'TASK-1', 'title': 'First', 'story_points': 3, 'status': 'active'},
            {'id': 'TASK-2', 'title': 'Second', 'story_points': 5, 'status': 'qa'},
        ]

        show_column("active", tasks, output_mode=OutputMode.AGENT)
        payload = json.loads(capsys.readouterr().out)
        assert payload["column"] == "active"
        assert payload["count"] == 2
        assert payload["tasks"][0]["id"] == "TASK-1"
