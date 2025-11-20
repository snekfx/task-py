"""Command implementations for task linking."""

import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_success, print_info
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    find_task_file,
    load_task,
    write_task,
    append_issue,
    read_issues,
    parse_task_ids,
)


def cmd_link(args):
    """Link references/issues to a task."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_ids = parse_task_ids(args.task_ids)
    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    failures = []

    for task_id in task_ids:
        result = find_task_file(task_id)
        if not result:
            print_error(f"Task not found: {task_id}")
            failures.append(task_id)
            continue

        path, _ = result

        try:
            task = load_task(task_id)

            if args.code:
                task.references["code"].extend(args.code)
            if args.docs:
                task.references["docs"].extend(args.docs)
            if args.plan:
                task.references["plans"].extend(args.plan)
            if args.test:
                task.references["tests"].extend(args.test)
            if args.nfr:
                task.nfrs.extend(args.nfr)
            if args.verify:
                task.verification["command"] = args.verify[0]
                task.verification["status"] = "pending"
            if args.commit:
                task.commit_hash = args.commit

            write_task(task)

            if args.issue:
                for desc in args.issue:
                    append_issue(path, desc)

            print_success(f"References linked to {task_id}")
        except Exception as exc:
            print_error(f"Failed to link references for {task_id}: {exc}")
            failures.append(task_id)

    if failures:
        sys.exit(1)


def cmd_issues(args):
    """Display issues tracked for a task."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    result = find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, _ = result
    issues = read_issues(path)

    if not issues:
        print_info(f"No issues tracked for {args.task_id}")
        return

    print_success(f"Issues for {args.task_id} ({len(issues)} found)")
    for issue in issues:
        print(f"  {issue}")
