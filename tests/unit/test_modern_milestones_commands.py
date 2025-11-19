"""Unit tests for modern milestones commands."""

import json
from argparse import Namespace

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.modern.milestones.commands import cmd_milestones, cmd_milestone
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
