"""Command implementations for core task management."""

import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error, print_info, get_output_mode
from taskpy.legacy.commands import _read_manifest, _sort_tasks, _format_title_column
from taskpy.modern.views import ListView, ColumnConfig


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def _read_manifest_with_filters(storage: TaskStorage, args):
    """Read manifest and apply filters."""
    rows = _read_manifest(storage)

    # Hide done/archived by default unless --all or --status=done/archived explicitly requested
    explicit_status_filter = hasattr(args, 'status') and args.status and args.status in ['done', 'archived']
    show_all = hasattr(args, 'all') and args.all
    if not show_all and not explicit_status_filter:
        rows = [r for r in rows if r['status'] not in ['done', 'archived']]

    # Apply filters
    if hasattr(args, 'epic') and args.epic:
        rows = [r for r in rows if r['epic'] == args.epic.upper()]

    if hasattr(args, 'status') and args.status:
        rows = [r for r in rows if r['status'] == args.status]

    if hasattr(args, 'priority') and args.priority:
        rows = [r for r in rows if r['priority'] == args.priority]

    if hasattr(args, 'milestone') and args.milestone:
        rows = [r for r in rows if r.get('milestone') == args.milestone]

    if hasattr(args, 'sprint') and args.sprint:
        sprint_value = 'true' if args.sprint else 'false'
        rows = [r for r in rows if r.get('in_sprint', 'false') == sprint_value]

    return rows


def cmd_list(args):
    """List tasks with optional filters using modern ListView."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and apply filters
    tasks = _read_manifest_with_filters(storage, args)

    if not tasks:
        print_info("No tasks found matching filters")
        return

    # Apply sorting
    sort_mode = getattr(args, 'sort', 'priority')
    tasks = _sort_tasks(tasks, sort_mode)

    # Configure columns
    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field=lambda t: _format_title_column(t.get('title'))),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Priority", field="priority"),
        ColumnConfig(name="Sprint", field=lambda t: '✓' if t.get('in_sprint', 'false') == 'true' else ''),
    ]

    # Create and render ListView
    view = ListView(
        data=tasks,
        columns=columns,
        title=f"Tasks ({len(tasks)} found)",
        output_mode=get_output_mode(),
        status_field='status',
        grey_done=True,
    )
    view.render()


__all__ = ['cmd_list']
