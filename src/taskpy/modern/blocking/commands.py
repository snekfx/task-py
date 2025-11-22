"""Command implementations for blocking/dependencies."""

import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_info, print_success
from taskpy.modern.workflow.commands import _move_task
from taskpy.modern.shared.tasks import (
    parse_task_ids,
    find_task_file,
    load_task_from_path,
    ensure_initialized,
)


def cmd_block(args):
    """Block task(s) with a required reason."""
    root = Path.cwd()
    ensure_initialized(root)

    task_ids = parse_task_ids(args.task_ids)
    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    failures = []

    for task_id in task_ids:
        result = find_task_file(task_id, root)
        if not result:
            print_error(f"Task not found: {task_id}")
            failures.append(task_id)
            continue

        path, _ = result
        task = load_task_from_path(path)

        if task.status == "blocked":
            print_info(f"Task {task_id} is already blocked")
            if task.blocked_reason:
                print_info(f"Reason: {task.blocked_reason}")
            continue

        task.blocked_reason = args.reason

        _move_task(
            task_id,
            path,
            "blocked",
            task=task,
            reason=args.reason,
            action="block",
            root=root,
        )
        print_success(f"{task_id} blocked")
        print_info(f"Reason: {args.reason}")

    if failures:
        sys.exit(1)


def cmd_unblock(args):
    """Unblock task(s) and send them back to backlog."""
    root = Path.cwd()
    ensure_initialized(root)

    task_ids = parse_task_ids(args.task_ids)
    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    failures = []

    for task_id in task_ids:
        result = find_task_file(task_id, root)
        if not result:
            print_error(f"Task not found: {task_id}")
            failures.append(task_id)
            continue

        path, _ = result
        task = load_task_from_path(path)

        if task.status != "blocked":
            print_info(f"Task {task_id} is not blocked (status: {task.status})")
            continue

        task.blocked_reason = None

        _move_task(
            task_id,
            path,
            "backlog",
            task=task,
            action="unblock",
            root=root,
        )
        print_success(f"{task_id} unblocked")

    if failures:
        sys.exit(1)


__all__ = ["cmd_block", "cmd_unblock"]
