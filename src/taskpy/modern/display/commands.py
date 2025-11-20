"""Command implementations for display/visualization features.

This module provides task visualization and analytics commands:
- info: Show task status and gate requirements
- stoplight: Validate gates with exit codes (for CI/automation)
- kanban: Display kanban board view
- history: Show task history/audit trail
- stats: Display project statistics

Migrated from legacy/commands.py (lines 812-946, 1208-1318, 1917-1968)
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from taskpy.legacy.models import Task, TaskStatus
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import (
    print_success,
    print_error,
    print_info,
    print_warning,
)
from taskpy.legacy.commands import _read_manifest, _sort_tasks
from taskpy.modern.shared.aggregations import (
    filter_by_epic,
    filter_by_milestone,
    get_project_stats,
)
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.utils import format_history_entry
from taskpy.modern.views import show_column, rolo_table


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


# Import validation function from workflow module
from taskpy.modern.workflow.commands import validate_promotion


# =============================================================================
# Display Commands
# =============================================================================

def cmd_info(args):
    """Show task status and gate requirements for next promotion."""
    storage = get_storage()
    mode = get_output_mode()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result
    task = storage.read_task_file(path)

    # Determine next status in workflow
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                TaskStatus.QA, TaskStatus.DONE]

    print_info(f"Task: {args.task_id}")
    print(f"Current Status: {current_status.value}")
    print(f"Title: {task.title}")
    print()

    if current_status == TaskStatus.BLOCKED:
        reason = task.blocked_reason or "No reason provided."
        print_warning(f"Task is blocked: {reason}")
        print("Resolve the blocker and run 'taskpy unblock' before promoting.")
        return

    if current_status == TaskStatus.REGRESSION:
        next_status = TaskStatus.QA
        print(f"Next Status: {next_status.value} (re-review after regression)")
        print()
    elif current_status in (TaskStatus.DONE, TaskStatus.ARCHIVED):
        print_success(f"Task is at final status ({current_status.value})")
        if current_status == TaskStatus.ARCHIVED:
            print("Archived tasks must be reactivated before additional work.")
        return
    elif current_status in workflow:
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_success("Task is at final status (done)")
            return
        next_status = workflow[current_idx + 1]
        print(f"Next Status: {next_status.value}")
        print()
    else:
        print_warning(f"Unknown workflow status: {current_status.value}")
        print("Cannot determine next status automatically.")
        return

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        print_success("✅ Ready to promote - all requirements met")
    else:
        print("Gate Requirements:")
        for blocker in blockers:
            print(f"  • {blocker}")


def cmd_stoplight(args):
    """Validate gate requirements and exit with status code.

    Exit codes:
    - 0: Ready to promote (all gates passed)
    - 1: Missing requirements (gate failure)
    - 2: Blocked or error
    """
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(2)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(2)

    path, current_status = result
    task = storage.read_task_file(path)

    # Check if task is blocked
    if task.status == TaskStatus.BLOCKED:
        reason = task.blocked_reason or "No reason provided"
        print_warning(f"Task {task.id} is blocked: {reason}")
        sys.exit(2)  # Blocked

    # Determine next status in workflow
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY,
                TaskStatus.ACTIVE, TaskStatus.QA, TaskStatus.DONE]

    if current_status == TaskStatus.REGRESSION:
        next_status = TaskStatus.QA
    else:
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_success(f"Task {task.id} is already at final status ({current_status.value})")
            sys.exit(0)
        next_status = workflow[current_idx + 1]

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        print_success(
            f"Ready: {task.id} can move {current_status.value} → {next_status.value}",
            "Stoplight"
        )
        sys.exit(0)
    else:
        print_warning(
            f"Missing requirements for {task.id}: {current_status.value} → {next_status.value}",
            "Stoplight"
        )
        for blocker in blockers:
            print(f"  • {blocker}")
        sys.exit(1)


def cmd_kanban(args):
    """Display kanban board."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    rows = _read_manifest(storage)
    epic_filter = getattr(args, 'epic', None)
    sort_mode = getattr(args, 'sort', 'priority')
    statuses = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY,
                TaskStatus.ACTIVE, TaskStatus.QA, TaskStatus.DONE]
    grouped: Dict[TaskStatus, List[Dict[str, Any]]] = {status: [] for status in statuses}

    for row in rows:
        if epic_filter and row['epic'] != epic_filter.upper():
            continue
        status = TaskStatus(row['status'])
        if status in grouped:
            grouped[status].append(row)

    for status in grouped:
        grouped[status] = _sort_tasks(grouped[status], sort_mode)

    if all(len(tasks) == 0 for tasks in grouped.values()):
        print_info("No tasks match the provided filters.")
        return

    mode = get_output_mode()
    if mode == OutputMode.AGENT:
        payload = {
            "filters": {
                "epic": epic_filter,
                "sort": sort_mode,
            },
            "columns": [
                {
                    "status": status.value,
                    "count": len(tasks),
                    "tasks": tasks,
                }
                for status, tasks in grouped.items() if tasks
            ],
        }
        print(json.dumps(payload, indent=2))
        return

    for status in statuses:
        tasks = grouped.get(status, [])
        if not tasks:
            continue
        show_column(status.value, tasks, output_mode=mode)
        if mode == OutputMode.PRETTY:
            print()


def cmd_history(args):
    """Display task history and audit trail."""
    storage = get_storage()
    mode = get_output_mode()

    # Check if showing all tasks or single task
    if getattr(args, 'all', False):
        # Read all tasks from manifest
        rows = _read_manifest(storage)

        # Collect all tasks with history
        tasks_with_history = []
        for row in rows:
            task_id = row['id']
            result = storage.find_task_file(task_id)
            if result:
                path, _ = result
                try:
                    task = storage.read_task_file(path)
                    if task.history:
                        tasks_with_history.append(task)
                except Exception:
                    continue

        if not tasks_with_history:
            print_info("No tasks with history entries found")
            return

        if mode == OutputMode.AGENT:
            payload = [
                {
                    "task_id": task.id,
                    "title": task.title,
                    "history": [
                        {
                            "timestamp": entry.timestamp.isoformat(),
                            "action": entry.action,
                            "from_status": entry.from_status,
                            "to_status": entry.to_status,
                            "reason": entry.reason,
                            "actor": entry.actor,
                            "metadata": entry.metadata,
                        }
                        for entry in task.history
                    ],
                }
                for task in tasks_with_history
            ]
            print(json.dumps(payload, indent=2))
            return

        total_entries = sum(len(t.history) for t in tasks_with_history)
        print_success(f"History for {len(tasks_with_history)} tasks ({total_entries} total entries)", "All Task History")
        print()

        for task in tasks_with_history:
            print(f"[{task.id}] {task.title}")
            for entry in task.history:
                for line in format_history_entry(entry):
                    print(line)
            print()
        return

    # Single task mode
    if not hasattr(args, 'task_id') or not args.task_id:
        print_error("Task ID required (or use --all to show all)")
        sys.exit(1)

    # Find task file
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result

    try:
        task = storage.read_task_file(path)

        if not task.history:
            print_info(f"No history entries for {args.task_id}")
            return

        if mode == OutputMode.AGENT:
            payload = {
                "task_id": task.id,
                "title": task.title,
                "history": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "action": entry.action,
                        "from_status": entry.from_status,
                        "to_status": entry.to_status,
                        "reason": entry.reason,
                        "actor": entry.actor,
                        "metadata": entry.metadata,
                    }
                    for entry in task.history
                ],
            }
            print(json.dumps(payload, indent=2))
            return

        print_success(f"History for {args.task_id} ({len(task.history)} entries)", "Task History")
        print()

        for entry in task.history:
            for line in format_history_entry(entry):
                print(line)

    except Exception as e:
        print_error(f"Error reading task history: {e}")
        sys.exit(1)


def cmd_stats(args):
    """Show task statistics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    rows = _read_manifest(storage)

    epic_filter = getattr(args, 'epic', None)
    if epic_filter:
        rows = filter_by_epic(rows, epic_filter)

    milestone_filter = getattr(args, 'milestone', None)
    if milestone_filter:
        rows = filter_by_milestone(rows, milestone_filter)

    stats = get_project_stats(rows)
    mode = get_output_mode()
    summary = {
        **stats,
        "filters": {
            "epic": epic_filter.upper() if epic_filter else None,
            "milestone": milestone_filter,
        },
    }

    if mode == OutputMode.AGENT:
        print(json.dumps(summary, indent=2))
        return

    print(f"\n{'='*50}")
    print("Task Statistics")
    if summary["filters"]["epic"]:
        print(f"Epic: {summary['filters']['epic']}")
    if summary["filters"]["milestone"]:
        print(f"Milestone: {summary['filters']['milestone']}")
    print(f"{'='*50}\n")

    print(f"Total Tasks: {summary['total_tasks']}")
    print(f"Total Story Points: {summary['total_story_points']}\n")

    status_rows = [
        [status, str(count)]
        for status, count in sorted(summary["by_status"].items())
        if count > 0
    ]

    if mode == OutputMode.PRETTY and status_rows:
        rolo_table(["Status", "Count"], status_rows, title="By Status")
    else:
        print("By Status:")
        for status, count in status_rows:
            print(f"  {status:15} {count}")

    print("\nBy Priority:")
    for priority, count in sorted(summary["by_priority"].items()):
        print(f"  {priority:15} {count}")
    print()


__all__ = ['cmd_info', 'cmd_stoplight', 'cmd_kanban', 'cmd_history', 'cmd_stats']
