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
from taskpy.modern.shared.messages import print_success, print_error, print_info, print_warning
from taskpy.modern.shared.tasks import (
    TaskRecord,
    ensure_initialized,
    find_task_file,
    load_task_from_path,
    load_manifest,
    sort_manifest_rows,
)
from taskpy.modern.shared.aggregations import (
    filter_by_epic,
    filter_by_milestone,
    get_project_stats,
)
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.utils import format_history_entry
from taskpy.modern.views import show_column, rolo_table

# Status constants
STATUS_STUB = "stub"
STATUS_BACKLOG = "backlog"
STATUS_READY = "ready"
STATUS_ACTIVE = "active"
STATUS_QA = "qa"
STATUS_REGRESSION = "regression"
STATUS_DONE = "done"
STATUS_ARCHIVED = "archived"
STATUS_BLOCKED = "blocked"


# Import validation function from workflow module
from taskpy.modern.workflow.commands import validate_promotion


# =============================================================================
# Display Commands
# =============================================================================

def cmd_info(args):
    """Show task status and gate requirements for next promotion."""
    root = Path.cwd()
    ensure_initialized(root)
    mode = get_output_mode()

    # Find task
    result = find_task_file(args.task_id, root)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result
    task = load_task_from_path(path)

    # Workflow order
    workflow = [STATUS_STUB, STATUS_BACKLOG, STATUS_READY, STATUS_ACTIVE, STATUS_QA, STATUS_DONE]

    print_info(f"Task: {args.task_id}")
    print(f"Current Status: {current_status}")
    print(f"Title: {task.title}")
    print()

    if current_status == STATUS_BLOCKED:
        reason = task.blocked_reason or "No reason provided."
        print_warning(f"Task is blocked: {reason}")
        print("Resolve the blocker and run 'taskpy unblock' before promoting.")
        return

    if current_status == STATUS_REGRESSION:
        next_status = STATUS_QA
        print(f"Next Status: {next_status} (re-review after regression)")
        print()
    elif current_status in (STATUS_DONE, STATUS_ARCHIVED):
        print_success(f"Task is at final status ({current_status})")
        if current_status == STATUS_ARCHIVED:
            print("Archived tasks must be reactivated before additional work.")
        return
    elif current_status in workflow:
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_success("Task is at final status (done)")
            return
        next_status = workflow[current_idx + 1]
        print(f"Next Status: {next_status}")
        print()
    else:
        print_warning(f"Unknown workflow status: {current_status}")
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
    root = Path.cwd()
    ensure_initialized(root)

    # Find task
    result = find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(2)

    path, current_status = result
    task = load_task_from_path(path)

    # Check if task is blocked
    if task.status == STATUS_BLOCKED:
        reason = task.blocked_reason or "No reason provided"
        print_warning(f"Task {task.id} is blocked: {reason}")
        sys.exit(2)  # Blocked

    # Determine next status in workflow
    workflow = [STATUS_STUB, STATUS_BACKLOG, STATUS_READY,
                STATUS_ACTIVE, STATUS_QA, STATUS_DONE]

    if current_status == STATUS_REGRESSION:
        next_status = STATUS_QA
    else:
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_success(f"Task {task.id} is already at final status ({current_status})")
            sys.exit(0)
        next_status = workflow[current_idx + 1]

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        print_success(
            f"Ready: {task.id} can move {current_status} → {next_status}",
            "Stoplight"
        )
        sys.exit(0)
    else:
        print_warning(
            f"Missing requirements for {task.id}: {current_status} → {next_status}",
            "Stoplight"
        )
        for blocker in blockers:
            print(f"  • {blocker}")
        sys.exit(1)


def cmd_kanban(args):
    """Display kanban board."""
    root = Path.cwd()
    ensure_initialized(root)

    rows = load_manifest(root)
    epic_filter = getattr(args, 'epic', None)
    sort_mode = getattr(args, 'sort', 'priority')
    statuses = [STATUS_STUB, STATUS_BACKLOG, STATUS_READY,
                STATUS_ACTIVE, STATUS_QA, STATUS_DONE]
    grouped: Dict[str, List[Dict[str, Any]]] = {status: [] for status in statuses}

    for row in rows:
        if epic_filter and row['epic'] != epic_filter.upper():
            continue
        status = row['status']
        if status in grouped:
            grouped[status].append(row)

    for status in grouped:
        grouped[status] = sort_manifest_rows(grouped[status], sort_mode)

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
                    "status": status,
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
        show_column(status, tasks, output_mode=mode)
        if mode == OutputMode.PRETTY:
            print()


def cmd_history(args):
    """Display task history and audit trail."""
    root = Path.cwd()
    mode = get_output_mode()

    # Check if showing all tasks or single task
    if getattr(args, 'all', False):
        # Read all tasks from manifest
        rows = load_manifest(root)

        # Collect all tasks with history
        tasks_with_history = []
        for row in rows:
            task_id = row['id']
            result = find_task_file(task_id)
            if result:
                path, _ = result
                try:
                    task = load_task_from_path(path)
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
                    "history": task.history,  # Already in dict format
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
    result = find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result

    try:
        task = load_task_from_path(path)

        if not task.history:
            print_info(f"No history entries for {args.task_id}")
            return

        if mode == OutputMode.AGENT:
            payload = {
                "task_id": task.id,
                "title": task.title,
                "history": task.history,  # Already in dict format
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
    root = Path.cwd()
    ensure_initialized(root)

    rows = load_manifest(root)

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
