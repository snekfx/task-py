"""Command implementations for epics management."""

import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error
from taskpy.modern.shared.output import get_output_mode
from taskpy.modern.views import ListView, ColumnConfig


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def cmd_epics(args):
    """List available epics using modern ListView."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    epics = storage.load_epics()

    # Convert epics dict to list of dicts for ListView
    epic_data = [
        {
            'epic': name,
            'description': epic.description[:50] if epic.description else '',
            'active': '✓' if epic.active else '✗',
            'budget': str(epic.story_point_budget) if epic.story_point_budget else '-',
        }
        for name, epic in sorted(epics.items())
    ]

    # Configure columns
    columns = [
        ColumnConfig(name="Epic", field="epic"),
        ColumnConfig(name="Description", field="description"),
        ColumnConfig(name="Active", field="active"),
        ColumnConfig(name="Budget", field="budget"),
    ]

    # Create and render ListView
    view = ListView(
        data=epic_data,
        columns=columns,
        title=f"Available Epics ({len(epics)})",
        output_mode=get_output_mode(),
        status_field=None,  # Epics don't have status
        grey_done=False,
    )
    view.display()


__all__ = ['cmd_epics']
