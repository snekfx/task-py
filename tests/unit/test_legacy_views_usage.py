"""Regression tests ensuring legacy commands display ListView output."""

from argparse import Namespace
from unittest.mock import MagicMock, patch

from taskpy.legacy import commands as legacy_cmds


def _sample_task(in_sprint: str = 'false'):
    return {
        "id": "TASK-01",
        "title": "Sample",
        "status": "backlog",
        "story_points": "1",
        "priority": "medium",
        "in_sprint": in_sprint,
    }


def test_legacy_cmd_list_displays_listview(monkeypatch):
    """cmd_list should call ListView.display() so DATA/AGENT output isn't dropped."""
    storage = MagicMock()
    storage.is_initialized.return_value = True
    monkeypatch.setattr(legacy_cmds, "get_storage", lambda: storage)
    monkeypatch.setattr(
        legacy_cmds,
        "_read_manifest_with_filters",
        lambda storage, args: [_sample_task()],
    )
    monkeypatch.setattr(legacy_cmds, "_sort_tasks", lambda tasks, sort_mode: tasks)

    args = Namespace(
        format="table",
        sort="priority",
        epic=None,
        status=None,
        priority=None,
        milestone=None,
        sprint=False,
        all=False,
    )

    with patch("taskpy.legacy.commands.ListView") as listview_cls:
        view = MagicMock()
        listview_cls.return_value = view
        legacy_cmds.cmd_list(args)
        view.display.assert_called_once()


def test_legacy_sprint_list_displays_listview(monkeypatch):
    """_cmd_sprint_list should also call ListView.display() exactly once."""
    storage = MagicMock()
    storage.is_initialized.return_value = True
    monkeypatch.setattr(legacy_cmds, "get_storage", lambda: storage)
    monkeypatch.setattr(
        legacy_cmds,
        "_read_manifest",
        lambda storage: [_sample_task(in_sprint='true')],
    )

    with patch("taskpy.legacy.commands.ListView") as listview_cls:
        view = MagicMock()
        listview_cls.return_value = view
        legacy_cmds._cmd_sprint_list(Namespace())
        view.display.assert_called_once()
