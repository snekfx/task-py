"""Command implementations for sprint management."""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from taskpy.modern.shared.messages import print_error, print_info, print_success, print_warning
from taskpy.modern.shared.output import get_output_mode, OutputMode
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
from taskpy.legacy.storage import TaskStorage


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

    updated = 0
    for row in sprint_tasks:
        result = find_task_file(row['id'])
        if result:
            task = load_task(row['id'])
            task.in_sprint = False
            task.updated = utc_now()
            write_task(task, update_manifest=False)
            updated += 1

    if updated:
        storage = TaskStorage(Path.cwd())
        try:
            storage.rebuild_manifest()
        except Exception as exc:
            print_warning(f"Encountered error refreshing manifest: {exc}")

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


def _cmd_sprint_dashboard(args):
    """Show smart sprint dashboard."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    sprint_meta = _load_sprint_metadata()

    if not sprint_meta:
        print_warning("No active sprint. Initialize one with: taskpy modern sprint init --title \"Sprint Name\"")
        print_info("\nShowing sprint task list instead:\n")
        _cmd_sprint_list(args)
        return

    rows = load_manifest()
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    total_sp = sum(int(r.get('story_points', 0)) for r in sprint_tasks)
    done_sp = sum(int(r.get('story_points', 0)) for r in sprint_tasks if r.get('status') == 'done')
    capacity_sp = sprint_meta.get('capacity_sp', 20)

    today = datetime.now().date()
    try:
        end_date = datetime.strptime(sprint_meta['end_date'], '%Y-%m-%d').date()
        days_remaining = (end_date - today).days
    except (ValueError, KeyError):
        days_remaining = None

    mode = get_output_mode()
    dashboard_payload = {
        "meta": sprint_meta,
        "stats": {
            "total_sp": total_sp,
            "done_sp": done_sp,
            "capacity_sp": capacity_sp,
            "days_remaining": days_remaining,
        },
        "tasks": sprint_tasks,
    }

    if mode == OutputMode.AGENT:
        print(json.dumps(dashboard_payload, indent=2))
        return

    if mode == OutputMode.DATA:
        print(f"Sprint: {sprint_meta.get('title', 'Untitled')}")
        print(f"Focus: {sprint_meta.get('focus', 'N/A')}")
        if days_remaining is not None:
            print(f"Days Remaining: {days_remaining}")
        print(f"Capacity: {total_sp}/{capacity_sp} SP (Done: {done_sp})")
        print("Tasks:")
        for task in sprint_tasks:
            print(f"  - {task.get('id')}: {task.get('title')} [{task.get('status')}] ({task.get('story_points', 0)} SP)")
        return

    print(f"\n{'='*70}")
    print(f"🏃 Sprint {sprint_meta.get('number', '?')}: {sprint_meta.get('title', 'Untitled')}")
    print(f"{'='*70}")
    print(f"Focus: {sprint_meta.get('focus', 'N/A')}")

    if days_remaining is not None:
        if days_remaining > 0:
            print(f"Days Remaining: {days_remaining}")
        elif days_remaining == 0:
            print("Days Remaining: Last day! 🏁")
        else:
            print(f"Days Remaining: Overdue by {abs(days_remaining)} days ⚠️")

    progress_pct = (done_sp / capacity_sp * 100) if capacity_sp > 0 else 0
    bar_width = 40
    filled = int(bar_width * progress_pct / 100)
    bar = '█' * filled + '░' * (bar_width - filled)
    print(f"\nProgress: [{bar}] {done_sp}/{capacity_sp} SP ({progress_pct:.0f}%)")
    print(f"{'='*70}\n")

    if not sprint_tasks:
        print_info("No tasks in sprint. Add tasks with: taskpy modern sprint add <task-id>")
        return

    status_order = ['active', 'qa', 'regression', 'ready', 'backlog', 'stub', 'blocked', 'done']
    by_status = {}
    for task in sprint_tasks:
        status = task.get('status', 'unknown')
        by_status.setdefault(status, []).append(task)

    status_emoji = {
        'active': '🔥',
        'qa': '🧪',
        'regression': '🔙',
        'ready': '📋',
        'backlog': '📦',
        'stub': '📝',
        'blocked': '🚫',
        'done': '✅'
    }

    for status in status_order:
        if status not in by_status:
            continue
        tasks = by_status[status]
        emoji = status_emoji.get(status, '•')
        print(f"{emoji} {status.upper()} ({len(tasks)} tasks)")
        print("-" * 70)
        for task in tasks:
            task_id = task.get('id', '?')
            title = task.get('title', 'Untitled')
            if len(title) > 45:
                title = title[:42] + "..."
            sp = task.get('story_points', '0')
            priority = task.get('priority', 'medium')[0].upper()
            blocked = " 🚫 BLOCKED" if task.get('blocked_reason') else ""
            print(f"  [{priority}] {task_id}: {title} ({sp} SP){blocked}")
        print()

    if done_sp >= capacity_sp:
        print("🎉 Sprint capacity reached! Consider: taskpy modern sprint complete")
    elif sprint_tasks and all(t.get('status') == 'done' for t in sprint_tasks):
        print("🎉 All sprint tasks done! Consider: taskpy modern sprint complete")


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


def _cmd_sprint_recommend(args):
    """Recommend tasks to add to sprint based on capacity and priority."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    sprint_meta = _load_sprint_metadata()
    if not sprint_meta:
        print_error("No active sprint. Initialize one with: taskpy modern sprint init")
        sys.exit(1)

    rows = load_manifest()
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    total_sp = sum(int(r.get('story_points', 0)) for r in sprint_tasks)
    capacity_sp = sprint_meta.get('capacity_sp', 20)
    remaining_sp = capacity_sp - total_sp

    print(f"\n{'='*70}")
    print("Sprint Recommendations")
    print(f"{'='*70}")
    print(f"Current Capacity: {total_sp}/{capacity_sp} SP")
    print(f"Remaining: {remaining_sp} SP\n")

    if remaining_sp <= 0:
        print_warning("Sprint is at or over capacity!")
        return

    candidates = []
    for row in rows:
        if row.get('in_sprint', 'false') == 'true':
            continue
        status = row.get('status', '')
        if status in ['done', 'archived']:
            continue
        if row.get('blocked_reason'):
            continue
        if status not in ['ready', 'backlog', 'active', 'stub']:
            continue

        priority = row.get('priority', 'low')
        priority_score = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}.get(priority, 1)
        sp = int(row.get('story_points', 0))
        if sp <= 0 or sp > remaining_sp:
            continue

        candidates.append({
            'row': row,
            'priority_score': priority_score,
            'sp': sp,
        })

    if not candidates:
        print_info("No suitable tasks found to recommend.")
        return

    candidates.sort(key=lambda x: (-x['priority_score'], x['sp']))

    recommendations = []
    running_sp = 0
    for candidate in candidates:
        if running_sp + candidate['sp'] <= remaining_sp:
            recommendations.append(candidate['row'])
            running_sp += candidate['sp']

    if not recommendations:
        print_info("No tasks fit in the remaining capacity.")
        return

    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field=lambda r: format_title(r.get('title', ''))),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Priority", field="priority"),
    ]

    view = ListView(
        data=recommendations,
        columns=columns,
        title=f"Sprint Recommendations ({running_sp} SP)",
        output_mode=get_output_mode(),
        status_field='status',
        grey_done=False,
    )
    view.display()

    if get_output_mode() == OutputMode.PRETTY:
        print("\nTo add tasks: taskpy modern sprint add <task-id>")


def cmd_sprint(args):
    """Route sprint subcommands."""
    subcommand_handlers = {
        'list': _cmd_sprint_list,
        'add': _cmd_sprint_add,
        'remove': _cmd_sprint_remove,
        'clear': _cmd_sprint_clear,
        'stats': _cmd_sprint_stats,
        'init': _cmd_sprint_init,
        'dashboard': _cmd_sprint_dashboard,
        'recommend': _cmd_sprint_recommend,
    }

    # Get subcommand
    subcommand = getattr(args, 'sprint_subcommand', None)

    if not subcommand:
        _cmd_sprint_dashboard(args)
        return

    handler = subcommand_handlers.get(subcommand)
    if handler:
        handler(args)
    else:
        print_error(f"Unknown sprint command: {subcommand}")
        sys.exit(1)


__all__ = ['cmd_sprint']
