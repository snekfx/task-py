"""Command implementations for sprint management."""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from taskpy.modern.shared.messages import print_error, print_info, print_success, print_warning
from taskpy.modern.shared.output import get_output_mode
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    load_manifest,
    load_task,
    write_task,
    find_task_file,
    format_title,
    utc_now,
    KANBAN_RELATIVE_PATH,
)
from taskpy.modern.views import ListView, ColumnConfig


def _kanban_root(root: Optional[Path] = None) -> Path:
    base = Path.cwd() if root is None else root
    return base / KANBAN_RELATIVE_PATH


def _get_sprint_metadata_path(root: Optional[Path] = None):
    """Get path to sprint metadata file."""
    return _kanban_root(root) / "info" / "sprint_current.json"


def _load_sprint_metadata(root: Optional[Path] = None):
    """Load sprint metadata from JSON file."""
    sprint_file = _get_sprint_metadata_path(root)

    if not sprint_file.exists():
        return None

    try:
        with open(sprint_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _save_sprint_metadata(metadata, root: Optional[Path] = None):
    """Save sprint metadata to JSON file."""
    sprint_file = _get_sprint_metadata_path(root)

    # Ensure directory exists
    sprint_file.parent.mkdir(parents=True, exist_ok=True)

    with open(sprint_file, 'w') as f:
        json.dump(metadata, f, indent=2)


def _cmd_sprint_list(args):
    """List all tasks in sprint using modern ListView."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    rows = load_manifest()
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Configure columns
    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field=lambda t: format_title(t.get('title', ''))),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Priority", field="priority"),
        ColumnConfig(name="Sprint", field=lambda t: '✓' if t.get('in_sprint', 'false') == 'true' else ''),
    ]

    # Create and render ListView
    view = ListView(
        data=sprint_tasks,
        columns=columns,
        title=f"Sprint Tasks ({len(sprint_tasks)} found)",
        output_mode=get_output_mode(),
        status_field='status',
        grey_done=True,
    )
    view.display()


def _cmd_sprint_add(args):
    """Add task to sprint."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_id = args.task_id.upper()
    result = find_task_file(task_id)
    if not result:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    task = load_task(task_id)

    # Check if already in sprint
    if task.in_sprint:
        print_warning(f"{task_id} is already in the sprint")
        return

    # Add to sprint
    task.in_sprint = True
    task.updated = utc_now()
    write_task(task)

    print_success(f"Added {task_id} to sprint")


def _cmd_sprint_remove(args):
    """Remove task from sprint."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_id = args.task_id.upper()
    result = find_task_file(task_id)
    if not result:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    task = load_task(task_id)

    # Check if in sprint
    if not task.in_sprint:
        print_warning(f"{task_id} is not in the sprint")
        return

    # Remove from sprint
    task.in_sprint = False
    task.updated = utc_now()
    write_task(task)

    print_success(f"Removed {task_id} from sprint")


def _cmd_sprint_clear(args):
    """Clear all tasks from sprint."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    rows = load_manifest()
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Remove all tasks from sprint
    for row in sprint_tasks:
        result = find_task_file(row['id'])
        if result:
            task = load_task(row['id'])
            task.in_sprint = False
            task.updated = utc_now()
            write_task(task)

    print_success(f"Cleared {len(sprint_tasks)} tasks from sprint")


def _cmd_sprint_stats(args):
    """Show sprint statistics."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    rows = load_manifest()
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Calculate statistics
    total_tasks = len(sprint_tasks)
    total_sp = sum(int(r.get('story_points', 0)) for r in sprint_tasks)

    # Group by status
    by_status = {}
    for row in sprint_tasks:
        status = row.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1

    # Group by priority
    by_priority = {}
    for row in sprint_tasks:
        priority = row.get('priority', 'unknown')
        by_priority[priority] = by_priority.get(priority, 0) + 1

    # Display statistics
    print(f"\n{'='*50}")
    print(f"Sprint Statistics")
    print(f"{'='*50}\n")

    print(f"Total Tasks: {total_tasks}")
    print(f"Total Story Points: {total_sp}\n")

    print("By Status:")
    for status in ['stub', 'backlog', 'ready', 'active', 'qa', 'regression', 'done', 'blocked']:
        count = by_status.get(status, 0)
        if count > 0:
            print(f"  {status:15} {count:3}")

    print("\nBy Priority:")
    for priority in ['critical', 'high', 'medium', 'low']:
        count = by_priority.get(priority, 0)
        if count > 0:
            print(f"  {priority:15} {count:3}")

    print()


def _cmd_sprint_init(args):
    """Initialize a new sprint with metadata."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    existing_sprint = _load_sprint_metadata()
    if existing_sprint and not getattr(args, 'force', False):
        print_error("Sprint already exists. Use --force to overwrite.")
        print_info(f"Current sprint: {existing_sprint.get('title', 'Untitled')}")
        sys.exit(1)

    # Get sprint number (increment from existing or start at 1)
    sprint_number = 1
    if existing_sprint:
        sprint_number = existing_sprint.get('number', 0) + 1

    # Create sprint metadata
    today = datetime.now().date()
    duration = getattr(args, 'duration', 14)
    end_date = today + timedelta(days=duration)

    metadata = {
        "number": sprint_number,
        "title": getattr(args, 'title', f"Sprint {sprint_number}"),
        "focus": getattr(args, 'focus', "General development"),
        "start_date": str(today),
        "end_date": str(end_date),
        "capacity_sp": getattr(args, 'capacity', 20),
        "goals": []
    }

    _save_sprint_metadata(metadata)
    print_success(f"Initialized {metadata['title']}")
    print_info(f"Duration: {metadata['start_date']} to {metadata['end_date']}")
    print_info(f"Capacity: {metadata['capacity_sp']} SP")


def cmd_sprint(args):
    """Route sprint subcommands."""
    subcommand_handlers = {
        'list': _cmd_sprint_list,
        'add': _cmd_sprint_add,
        'remove': _cmd_sprint_remove,
        'clear': _cmd_sprint_clear,
        'stats': _cmd_sprint_stats,
        'init': _cmd_sprint_init,
    }

    # Get subcommand
    subcommand = getattr(args, 'sprint_subcommand', None)

    if not subcommand:
        print_error("Sprint subcommand required. Use: taskpy modern sprint list")
        sys.exit(1)

    handler = subcommand_handlers.get(subcommand)
    if handler:
        handler(args)
    else:
        print_error(f"Unknown sprint command: {subcommand}")
        sys.exit(1)


__all__ = ['cmd_sprint']
