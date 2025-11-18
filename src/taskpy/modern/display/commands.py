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
from pathlib import Path
from typing import List, Dict, Any, Optional
from taskpy.legacy.models import Task, TaskStatus
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import (
    print_success,
    print_error,
    print_info,
    print_warning,
    display_kanban_column
)
from taskpy.legacy.commands import _read_manifest, _sort_tasks


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

    # Group tasks by status
    tasks_by_status = {}
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                   TaskStatus.QA, TaskStatus.DONE]:
        tasks_by_status[status] = []

    # Read all tasks from manifest
    manifest_rows = _read_manifest(storage)

    # Filter by epic if specified
    epic_filter = getattr(args, 'epic', None)
    for row in manifest_rows:
        if epic_filter and row['epic'] != epic_filter.upper():
            continue

        status = TaskStatus(row['status'])
        if status in tasks_by_status:
            tasks_by_status[status].append(row)

    # Apply sorting to each column
    sort_mode = getattr(args, 'sort', 'priority')
    for status in tasks_by_status:
        tasks_by_status[status] = _sort_tasks(tasks_by_status[status], sort_mode)

    # Display columns
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                   TaskStatus.QA, TaskStatus.DONE]:
        display_kanban_column(status.value, tasks_by_status[status])


def cmd_history(args):
    """Display task history and audit trail."""
    storage = get_storage()

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

        # Display all history
        total_entries = sum(len(t.history) for t in tasks_with_history)
        print_success(f"History for {len(tasks_with_history)} tasks ({total_entries} total entries)", "All Task History")
        print()

        for task in tasks_with_history:
            print(f"[{task.id}] {task.title}")
            for entry in task.history:
                # Convert to local timezone
                local_time = entry.timestamp.astimezone()
                timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")
                action = entry.action

                # Format based on action type
                if entry.from_status and entry.to_status:
                    transition = f"{entry.from_status} → {entry.to_status}"
                    action_display = f"{action}: {transition}"
                else:
                    action_display = action

                print(f"  [{timestamp}] {action_display}")
                if entry.reason:
                    print(f"    Reason: {entry.reason}")
                if entry.actor:
                    print(f"    Actor: {entry.actor}")
                if entry.metadata:
                    for key, value in entry.metadata.items():
                        print(f"    {key}: {value}")
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

        # Display history in chronological order
        print_success(f"History for {args.task_id} ({len(task.history)} entries)", "Task History")
        print()

        for entry in task.history:
            # Convert to local timezone
            local_time = entry.timestamp.astimezone()
            timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")
            action = entry.action

            # Format based on action type
            if entry.from_status and entry.to_status:
                transition = f"{entry.from_status} → {entry.to_status}"
                action_display = f"{action}: {transition}"
            else:
                action_display = action

            print(f"  [{timestamp}] {action_display}")
            if entry.reason:
                print(f"    Reason: {entry.reason}")
            if entry.actor:
                print(f"    Actor: {entry.actor}")
            if entry.metadata:
                for key, value in entry.metadata.items():
                    print(f"    {key}: {value}")

    except Exception as e:
        print_error(f"Error reading task history: {e}")
        sys.exit(1)


def cmd_stats(args):
    """Show task statistics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest
    rows = _read_manifest(storage)

    # Filter by epic if specified
    epic_filter = getattr(args, 'epic', None)
    if epic_filter:
        rows = [r for r in rows if r['epic'] == epic_filter.upper()]

    # Filter by milestone if specified
    milestone_filter = getattr(args, 'milestone', None)
    if milestone_filter:
        rows = [r for r in rows if r.get('milestone') == milestone_filter]

    # Calculate stats
    total = len(rows)
    by_status = {}
    by_priority = {}
    total_sp = 0

    for row in rows:
        status = row['status']
        priority = row['priority']
        sp = int(row['story_points'])

        by_status[status] = by_status.get(status, 0) + 1
        by_priority[priority] = by_priority.get(priority, 0) + 1
        total_sp += sp

    # Display
    print(f"\n{'='*50}")
    print(f"Task Statistics")
    if epic_filter:
        print(f"Epic: {epic_filter.upper()}")
    if milestone_filter:
        print(f"Milestone: {milestone_filter}")
    print(f"{'='*50}\n")

    print(f"Total Tasks: {total}")
    print(f"Total Story Points: {total_sp}\n")

    print("By Status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status:15} {count:3}")

    print("\nBy Priority:")
    for priority, count in sorted(by_priority.items()):
        print(f"  {priority:15} {count:3}")

    print()


__all__ = ['cmd_info', 'cmd_stoplight', 'cmd_kanban', 'cmd_history', 'cmd_stats']
