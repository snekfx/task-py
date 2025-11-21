"""Command implementations for milestones management."""

import sys
import re
import json
from pathlib import Path
from typing import Optional

from taskpy.modern.shared.aggregations import (
    filter_by_milestone,
    get_milestone_stats,
)
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.messages import print_error, print_info, print_success, print_warning
from taskpy.modern.shared.tasks import (
    ensure_initialized,
    load_manifest,
    load_milestones as load_milestones_data,
    find_task_file,
    load_task_from_path,
    write_task,
    _info_dir,
)
from taskpy.modern.views import ListView, ColumnConfig


def _update_milestone_status(milestone_id: str, new_status: str, root: Optional[Path] = None):
    """Update milestone status in TOML file."""
    info_dir = _info_dir(root)
    milestones_file = info_dir / "milestones.toml"
    content = milestones_file.read_text()

    # Find the milestone section and update status
    # Pattern: [milestone-id]\n... status = "old_status" ... next [section or EOF
    pattern = rf'(\[{re.escape(milestone_id)}\][^\[]*status\s*=\s*")[^"]*(")'
    replacement = rf'\g<1>{new_status}\g<2>'

    updated_content = re.sub(pattern, replacement, content)

    if updated_content == content:
        # If pattern didn't match, milestone might not have a status field
        # Try to add it after the milestone header
        pattern = rf'(\[{re.escape(milestone_id)}\]\n)'
        if re.search(pattern, content):
            replacement = rf'\g<1>status = "{new_status}"\n'
            updated_content = re.sub(pattern, replacement, content, count=1)

    milestones_file.write_text(updated_content)


def cmd_milestones(args):
    """List all milestones sorted by priority."""
    ensure_initialized()

    milestones = load_milestones_data()

    if not milestones:
        print_info("No milestones defined. Add them to: data/kanban/info/milestones.toml")
        return

    # Sort by priority and prepare rows for ListView rendering
    sorted_milestones = sorted(milestones.items(), key=lambda x: x[1].priority)
    rows = [
        {
            "id": milestone_id,
            "name": milestone.name,
            "status": milestone.status,
            "priority": str(milestone.priority),
            "goal": str(milestone.goal_sp) if milestone.goal_sp else "-",
            "blocked": milestone.blocked_reason or "",
            "description": (milestone.description or "")[:80],
        }
        for milestone_id, milestone in sorted_milestones
    ]

    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Name", field="name"),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="Priority", field="priority"),
        ColumnConfig(name="Goal SP", field="goal"),
        ColumnConfig(name="Blocked Reason", field="blocked"),
    ]

    view = ListView(
        data=rows,
        columns=columns,
        title=f"Milestones ({len(rows)})",
        output_mode=get_output_mode(),
        status_field=None,
        grey_done=False,
    )
    view.display()


def cmd_milestone(args):
    """Route milestone subcommands."""
    if not args.milestone_command:
        print_error("Please specify a milestone subcommand: show, start, complete, assign")
        sys.exit(1)

    # Route to subcommand handler
    subcommand_handlers = {
        'show': _cmd_milestone_show,
        'start': _cmd_milestone_start,
        'complete': _cmd_milestone_complete,
        'assign': _cmd_milestone_assign,
    }

    handler = subcommand_handlers.get(args.milestone_command)
    if handler:
        handler(args)
    else:
        print_error(f"Unknown milestone subcommand: {args.milestone_command}")
        sys.exit(1)


def _cmd_milestone_show(args):
    """Show milestone details and task statistics."""
    ensure_initialized()

    # Load milestone
    milestones = load_milestones_data()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    # Get tasks for this milestone
    rows = load_manifest()
    milestone_tasks = filter_by_milestone(rows, args.milestone_id)
    stats = get_milestone_stats(milestone_tasks)

    mode = get_output_mode()
    if mode == OutputMode.DATA:
        print(f"ID: {args.milestone_id}")
        print(f"Name: {milestone.name}")
        print(f"Priority: {milestone.priority}")
        print(f"Status: {milestone.status}")
        if milestone.goal_sp:
            print(f"Goal: {milestone.goal_sp} SP")
        if milestone.blocked_reason:
            print(f"Blocked: {milestone.blocked_reason}")
        print(f"Description: {milestone.description}")
        print(f"Tasks: {stats['total_tasks']} ({stats['completed_tasks']} completed)")
        for task in milestone_tasks:
            print(f"  - {task['id']} [{task['status']}] {task['title']}")
        return
    if mode == OutputMode.AGENT:
        payload = {
            "id": args.milestone_id,
            "name": milestone.name,
            "priority": milestone.priority,
            "status": milestone.status,
            "goal_sp": milestone.goal_sp,
            "blocked_reason": milestone.blocked_reason,
            "description": milestone.description,
            "stats": {
                "total_tasks": stats["total_tasks"],
                "completed_tasks": stats["completed_tasks"],
                "story_points_completed": stats["story_points_completed"],
                "story_points_total": stats["story_points_total"],
                "story_points_remaining": stats["story_points_remaining"],
                "by_status": stats["by_status"],
            },
            "tasks": milestone_tasks,
        }
        print(json.dumps(payload, indent=2))
        return

    status_emoji = {
        'active': '🟢',
        'planned': '⚪',
        'blocked': '🔴',
        'completed': '✅'
    }.get(milestone.status, '⚪')

    print(f"\n{status_emoji} {milestone.name}")
    print(f"{'='*60}")
    print(f"ID: {args.milestone_id}")
    print(f"Priority: {milestone.priority}")
    print(f"Status: {milestone.status}")
    if milestone.goal_sp:
        print(f"Goal: {milestone.goal_sp} SP")
    print(f"\n{milestone.description}\n")

    if milestone.blocked_reason:
        print(f"⚠️  Blocked: {milestone.blocked_reason}\n")

    print(f"Task Progress:")
    print(f"  Total Tasks: {stats['total_tasks']}")
    print(f"  Completed: {stats['completed_tasks']} / {stats['total_tasks']}")
    if stats["story_points_total"]:
        print(
            f"  Story Points: {stats['story_points_completed']} / {stats['story_points_total']} "
            f"completed ({stats['story_points_remaining']} remaining)"
        )
    else:
        print("  Story Points: 0")
    if milestone.goal_sp:
        progress_pct = (
            stats["story_points_completed"] / milestone.goal_sp * 100
            if milestone.goal_sp > 0
            else 0
        )
        print(f"  Goal Progress: {progress_pct:.1f}%")

    if stats["by_status"]:
        print(f"\nBy Status:")
        for status, count in sorted(stats["by_status"].items()):
            print(f"  {status:15} {count:3}")

    print()


def _cmd_milestone_start(args):
    """Mark milestone as active."""
    ensure_initialized()

    # Load milestones
    milestones = load_milestones_data()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    if milestone.status == 'active':
        print_info(f"Milestone {args.milestone_id} is already active")
        return

    # Update status in TOML file
    _update_milestone_status(args.milestone_id, 'active')

    print_success(
        f"Milestone {args.milestone_id} marked as active\n"
        f"Name: {milestone.name}",
        "Milestone Started"
    )


def _cmd_milestone_complete(args):
    """Mark milestone as completed."""
    ensure_initialized()

    # Load milestones
    milestones = load_milestones_data()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    if milestone.status == 'completed':
        print_info(f"Milestone {args.milestone_id} is already completed")
        return

    # Check if all tasks are done
    rows = load_manifest()
    milestone_tasks = [r for r in rows if r.get('milestone') == args.milestone_id]
    incomplete = [r for r in milestone_tasks if r['status'] not in ['done', 'archived']]

    if incomplete:
        print_warning(
            f"Milestone has {len(incomplete)} incomplete tasks:\n" +
            "\n".join(f"  - {t['id']}: {t['title']}" for t in incomplete[:5])
        )
        if len(incomplete) > 5:
            print_warning(f"  ... and {len(incomplete) - 5} more")
        print_warning("\nMarking as completed anyway.")

    # Update status in TOML file
    _update_milestone_status(args.milestone_id, 'completed')

    print_success(
        f"Milestone {args.milestone_id} marked as completed\n"
        f"Name: {milestone.name}",
        "Milestone Completed"
    )


def _cmd_milestone_assign(args):
    """Assign task to milestone."""
    ensure_initialized()

    # Validate milestone exists
    milestones = load_milestones_data()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    # Find task
    result = find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result

    try:
        # Read task
        task = load_task_from_path(path)
        old_milestone = task.milestone

        # Update milestone
        task.milestone = args.milestone_id

        # Save task
        write_task(task)

        if old_milestone:
            print_success(
                f"Moved {args.task_id} from {old_milestone} to {args.milestone_id}",
                "Task Reassigned"
            )
        else:
            print_success(
                f"Assigned {args.task_id} to {args.milestone_id}",
                "Task Assigned"
            )

    except Exception as e:
        print_error(f"Failed to assign task: {e}")
        sys.exit(1)
