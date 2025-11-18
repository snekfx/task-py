"""Command implementations for core task management."""

import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error, print_info, get_output_mode, OutputMode, display_task_card
from taskpy.legacy.commands import _read_manifest, _sort_tasks, _format_title_column, parse_task_ids
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


def cmd_show(args):
    """Display one or more tasks."""
    storage = get_storage()

    if not storage.is_initialized():
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
        result = storage.find_task_file(task_id)
        if not result:
            print_error(f"Task not found: {task_id}")
            continue

        path, status = result
        try:
            task = storage.read_task_file(path)
            tasks_to_display.append(task)
        except Exception as e:
            print_error(f"Failed to read task {task_id}: {e}")
            continue

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
            'status': task.status.value,
            'priority': task.priority.value,
            'story_points': task.story_points,
            'tags': task.tags,
            'dependencies': task.dependencies,
            'assigned': task.assigned,
            'content': task.content,
        }

        # Add references if present
        if task.references.code or task.references.docs:
            references_list = []
            if task.references.code:
                references_list.append(f"Code: {', '.join(task.references.code)}")
            if task.references.docs:
                references_list.append(f"Docs: {', '.join(task.references.docs)}")
            task_dict['references'] = '\n'.join(references_list)

        display_task_card(task_dict)

        # Show metadata if in data mode
        if get_output_mode() == OutputMode.DATA:
            print(f"\nCreated: {task.created.isoformat()}")
            print(f"Updated: {task.updated.isoformat()}")
            if task.nfrs:
                print(f"NFRs: {', '.join(task.nfrs)}")
            if task.references.code:
                print(f"Code: {', '.join(task.references.code)}")
            if task.references.docs:
                print(f"Docs: {', '.join(task.references.docs)}")
            if task.verification.command:
                print(f"Verification: {task.verification.command}")
                print(f"Status: {task.verification.status.value}")
            if task.resolution:
                print(f"\nResolution: {task.resolution.value}")
                print(f"Reason: {task.resolution_reason}")
                if task.duplicate_of:
                    print(f"Duplicate of: {task.duplicate_of}")


__all__ = ['cmd_list', 'cmd_show']
