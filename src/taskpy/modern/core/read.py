"""Read operations for core task management (list, show)."""

import sys
from pathlib import Path
from typing import List, Dict, Callable

from taskpy.modern.shared.messages import print_error, print_info
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    load_manifest,
    load_task,
    parse_task_ids,
    sort_manifest_rows,
    format_title,
)
from taskpy.modern.views import ListView, ColumnConfig, show_card


def _normalize_tags(value) -> List[str]:
    """Return list of tags from either list or comma-separated string."""
    if isinstance(value, list):
        return [t for t in value if t]
    return [t.strip() for t in str(value).split(",") if t.strip()]


def _column_builders() -> Dict[str, Callable[[], ColumnConfig]]:
    """Return mapping of column keywords to ColumnConfig builders."""
    return {
        "id": lambda: ColumnConfig(name="ID", field="id"),
        "title": lambda: ColumnConfig(name="Title", field=lambda t: format_title(t.get('title', ''))),
        "status": lambda: ColumnConfig(name="Status", field="status"),
        "sp": lambda: ColumnConfig(name="SP", field="story_points"),
        "story_points": lambda: ColumnConfig(name="SP", field="story_points"),
        "priority": lambda: ColumnConfig(name="Priority", field="priority"),
        "sprint": lambda: ColumnConfig(name="Sprint", field=lambda t: '✓' if t.get('in_sprint', 'false') == 'true' else ''),
        "tags": lambda: ColumnConfig(name="Tags", field=lambda t: ", ".join(_normalize_tags(t.get('tags', [])))),
        "milestone": lambda: ColumnConfig(name="Milestone", field="milestone"),
        "epic": lambda: ColumnConfig(name="Epic", field="epic"),
        "assigned": lambda: ColumnConfig(name="Assigned", field="assigned"),
    }


def _build_columns(selected: List[str]) -> List[ColumnConfig]:
    """Build column configs from a user selection."""
    default = ["id", "title", "status", "sp", "priority", "sprint"]
    names = selected or default
    builders = _column_builders()
    cols: List[ColumnConfig] = []
    for name in names:
        key = name.strip().lower()
        # alias handling
        if key == "story_points":
            key = "sp"
        if key not in builders:
            print_error(f"Unknown column: {name}. Valid: {', '.join(sorted(builders.keys()))}")
            sys.exit(1)
        cols.append(builders[key]())
    return cols


def _read_manifest_with_filters(args):
    """Read manifest and apply filters."""
    rows = load_manifest(Path.cwd())

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

    if hasattr(args, 'assigned') and args.assigned:
        rows = [r for r in rows if r.get('assigned') == args.assigned]

    if hasattr(args, 'tags') and args.tags:
        filter_tags = {
            tag.strip().lower()
            for tag in args.tags.split(',')
            if tag.strip()
        }
        rows = [
            r for r in rows
            if filter_tags.intersection({
                tag.strip().lower()
                for tag in r.get('tags', '').split(',')
                if tag.strip()
            })
        ]

    if hasattr(args, 'milestone') and args.milestone:
        rows = [r for r in rows if r.get('milestone') == args.milestone]

    if hasattr(args, 'sprint') and args.sprint:
        sprint_value = 'true' if args.sprint else 'false'
        rows = [r for r in rows if r.get('in_sprint', 'false') == sprint_value]

    return rows


def cmd_list(args):
    """List tasks with optional filters using modern ListView."""
    try:
        tasks = _read_manifest_with_filters(args)
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    if not tasks:
        print_info("No tasks found matching filters")
        return

    # Apply sorting
    sort_mode = getattr(args, 'sort', 'priority')
    tasks = sort_manifest_rows(tasks, sort_mode)

    mode = get_output_mode()
    format_mode = getattr(args, 'format', 'table')
    selected_columns = []
    if getattr(args, "columns", None):
        selected_columns = [c.strip() for c in args.columns.split(",") if c.strip()]
    columns = _build_columns(selected_columns)

    if format_mode == 'ids':
        for task in tasks:
            print(task['id'])
        return

    if format_mode == 'tsv':
        headers = [col.name for col in columns]
        print("\t".join(headers))
        for task in tasks:
            row = [col.get_value(task) for col in columns]
            print("\t".join(row))
        return

    if format_mode == 'cards':
        for task in tasks:
            show_card(
                {
                    'id': task['id'],
                    'title': task.get('title', ''),
                    'status': task.get('status', ''),
                    'priority': task.get('priority', 'medium'),
                    'story_points': int(task.get('story_points', 0)),
                    'tags': [t.strip() for t in task.get('tags', '').split(',') if t.strip()],
                    'dependencies': [d.strip() for d in task.get('dependencies', '').split(',') if d.strip()],
                    'assigned': task.get('assigned'),
                },
                output_mode=mode,
            )
            if mode != OutputMode.DATA:
                print()
        return

    # Configure columns
    # Create and render ListView
    view = ListView(
        data=tasks,
        columns=columns,
        title=f"Tasks ({len(tasks)} found)",
        output_mode=mode,
        status_field='status',
        grey_done=True,
    )
    view.display()


def cmd_show(args):
    """Display one or more tasks."""
    try:
        load_manifest(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Parse task IDs - support both space-separated and comma-delimited
    task_ids = parse_task_ids(args.task_ids)

    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    # Collect all tasks
    tasks_to_display = []
    for task_id in task_ids:
        try:
            task = load_task(task_id, Path.cwd())
            tasks_to_display.append(task)
        except FileNotFoundError:
            print_error(f"Task not found: {task_id}")
        except Exception as exc:
            print_error(f"Failed to read task {task_id}: {exc}")

    if not tasks_to_display:
        print_error("No valid tasks to display")
        sys.exit(1)

    # Display tasks
    for i, task in enumerate(tasks_to_display):
        # Add divider between tasks (except before first)
        if i > 0:
            if get_output_mode() == OutputMode.DATA:
                print("\n" + "=" * 80 + "\n")
            else:
                print()  # Just blank line in boxy mode (boxy handles dividers)

        # Display as card
        task_dict = {
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority,
            'story_points': task.story_points,
            'tags': task.tags,
            'dependencies': task.dependencies,
            'assigned': task.assigned,
            'content': task.content,
        }

        # Add references if present
        references = task.references
        if references.get('code') or references.get('docs'):
            references_list = []
            if references.get('code'):
                references_list.append(f"Code: {', '.join(references['code'])}")
            if references.get('docs'):
                references_list.append(f"Docs: {', '.join(references['docs'])}")
            task_dict['references'] = '\n'.join(references_list)

        show_card(task_dict, output_mode=get_output_mode())

        # Show metadata if in data mode
        if get_output_mode() == OutputMode.DATA:
            print(f"\nCreated: {task.created.isoformat()}")
            print(f"Updated: {task.updated.isoformat()}")
            if task.nfrs:
                print(f"NFRs: {', '.join(task.nfrs)}")
            if references.get('code'):
                print(f"Code: {', '.join(references['code'])}")
            if references.get('docs'):
                print(f"Docs: {', '.join(references['docs'])}")
            verification = task.verification
            if verification.get('command'):
                print(f"Verification: {verification['command']}")
                if verification.get('status'):
                    print(f"Status: {verification['status']}")
            if task.resolution:
                print(f"\nResolution: {task.resolution}")
                print(f"Reason: {task.resolution_reason}")
                if task.duplicate_of:
                    print(f"Duplicate of: {task.duplicate_of}")


__all__ = ['cmd_list', 'cmd_show']
