"""Command implementations for blocking/dependencies."""

import sys
from pathlib import Path

from taskpy.legacy.models import TaskStatus
from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.workflow.commands import _move_task
from taskpy.modern.shared.utils import require_initialized, load_task_or_exit
from taskpy.modern.shared.tasks import parse_task_ids


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def cmd_block(args):
    """Block task(s) with a required reason."""
    storage = get_storage()

    require_initialized(storage)

    task_ids = parse_task_ids(args.task_ids)
    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    failures = []

    for task_id in task_ids:
        try:
            task, path, _ = load_task_or_exit(storage, task_id)
        except SystemExit:
            failures.append(task_id)
            continue

        if task.status == TaskStatus.BLOCKED:
            print_info(f"Task {task_id} is already blocked")
            if task.blocked_reason:
                print_info(f"Reason: {task.blocked_reason}")
            continue

        task.blocked_reason = args.reason

        _move_task(
            storage,
            task_id,
            path,
            TaskStatus.BLOCKED,
            task,
            reason=args.reason,
            action="block",
        )
        print_success(f"{task_id} blocked")
        print_info(f"Reason: {args.reason}")

    if failures:
        sys.exit(1)


def cmd_unblock(args):
    """Unblock task(s) and send them back to backlog."""
    storage = get_storage()

    require_initialized(storage)

    task_ids = parse_task_ids(args.task_ids)
    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    failures = []

    for task_id in task_ids:
        try:
            task, path, _ = load_task_or_exit(storage, task_id)
        except SystemExit:
            failures.append(task_id)
            continue

        if task.status != TaskStatus.BLOCKED:
            print_info(f"Task {task_id} is not blocked (status: {task.status.value})")
            continue

        target_status = TaskStatus.BACKLOG
        task.blocked_reason = None

        _move_task(
            storage,
            task_id,
            path,
            target_status,
            task,
            action="unblock",
        )
        print_success(f"{task_id} unblocked")

    if failures:
        sys.exit(1)


__all__ = ["cmd_block", "cmd_unblock"]
