"""Unit tests for modern milestones commands."""

import json
from argparse import Namespace

# TOML parsing - use built-in tomllib on Python 3.11+, fallback to tomli
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.modern.milestones.commands import cmd_milestones, cmd_milestone, _update_milestone_status
from taskpy.modern.shared.output import set_output_mode, OutputMode


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_cmd_milestones_data_mode(tmp_path, monkeypatch, capsys):
    """Milestones list should render TSV output in DATA mode."""
    _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    set_output_mode(OutputMode.DATA)
    cmd_milestones(Namespace())

    output = capsys.readouterr().out
    assert "ID\tName\tStatus" in output
    assert "milestone-1" in output
    assert "Foundation MVP" in output


def test_cmd_milestone_show_agent_mode(tmp_path, monkeypatch, capsys):
    """Milestone show should emit JSON payload in agent mode."""
    storage = _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    task = Task(
        id="FEAT-001",
        epic="FEAT",
        number=1,
        title="Feature work",
        status=TaskStatus.ACTIVE,
        story_points=5,
        priority=Priority.HIGH,
        milestone="milestone-1",
    )
    storage.write_task_file(task)

    set_output_mode(OutputMode.AGENT)
    cmd_milestone(Namespace(milestone_command='show', milestone_id='milestone-1'))

    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "milestone-1"
    assert payload["status"] == "active"
    assert payload["stats"]["total_tasks"] == 1
    assert payload["tasks"][0]["id"] == "FEAT-001"


def test_update_milestone_status_toml_parsing(tmp_path, monkeypatch):
    """_update_milestone_status should use proper TOML parsing, not regex."""
    storage = _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    milestones_file = storage.kanban / "info" / "milestones.toml"

    # Read original TOML to verify it exists
    with open(milestones_file, 'rb') as f:
        original_data = tomllib.load(f)
    
    # Verify milestone-1 exists and has original status
    assert "milestone-1" in original_data
    assert original_data["milestone-1"]["status"] == "active"
    
    # Update status using the function
    _update_milestone_status("milestone-1", "completed", root=tmp_path)
    
    # Read back and verify update worked
    with open(milestones_file, 'rb') as f:
        updated_data = tomllib.load(f)
    
    # Status should be updated
    assert updated_data["milestone-1"]["status"] == "completed"
    
    # Other fields should be preserved
    assert updated_data["milestone-1"]["name"] == original_data["milestone-1"]["name"]
    assert updated_data["milestone-1"]["priority"] == original_data["milestone-1"]["priority"]
    assert updated_data["milestone-1"]["goal_sp"] == original_data["milestone-1"]["goal_sp"]
    
    # Other milestones should be unchanged
    assert "milestone-2" in updated_data
    assert updated_data["milestone-2"] == original_data["milestone-2"]


def test_update_milestone_status_nonexistent(tmp_path, monkeypatch):
    """_update_milestone_status should raise ValueError for nonexistent milestone."""
    import pytest
    storage = _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)
    
    # Try to update nonexistent milestone
    with pytest.raises(ValueError, match="not found"):
        _update_milestone_status("milestone-999", "active", root=tmp_path)
