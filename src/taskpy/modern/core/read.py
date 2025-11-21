"""Read operations for core task management (list, show)."""

import sys
from pathlib import Path

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

    if format_mode == 'ids':
        for task in tasks:
            print(task['id'])
        return

    if format_mode == 'tsv':
        print("\t".join(["id", "epic", "status", "title", "sp", "priority"]))
        for task in tasks:
            print(f"{task['id']}\t{task['epic']}\t{task['status']}\t{task['title']}\t{task['story_points']}\t{task['priority']}")
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
    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field=lambda t: format_title(t.get('title', ''))),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Priority", field="priority"),
        ColumnConfig(name="Sprint", field=lambda t: '✓' if t.get('in_sprint', 'false') == 'true' else ''),
        ColumnConfig(name="Tags", field=lambda t: ", ".join(t.get('tags', []))),
    ]

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
