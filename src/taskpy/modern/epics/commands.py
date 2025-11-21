"""Command implementations for epics management."""

import sys

from taskpy.modern.shared.messages import print_error
from taskpy.modern.shared.output import get_output_mode
from taskpy.modern.shared.tasks import ensure_initialized, load_epics
from taskpy.modern.views import ListView, ColumnConfig


def cmd_epics(args):
    """List available epics using modern ListView."""
    ensure_initialized()

    epics = load_epics()

    # Convert epics dict to list of dicts for ListView
    epic_data = [
        {
            'epic': name,
            'description': epic.get('description', '')[:50],
            'active': '✓' if epic.get('active', True) else '✗',
            'budget': str(epic.get('story_point_budget')) if epic.get('story_point_budget') else '-',
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
