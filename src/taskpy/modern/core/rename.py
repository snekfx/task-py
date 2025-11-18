"""Rename operations for core task management."""

import re
import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_info, print_success
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    find_task_file,
    load_task,
    make_task_id,
    parse_task_id,
    remove_manifest_entry,
    write_task,
)


def cmd_rename(args):
    """
    Rename a task's ID (epic and/or number).
    Updates frontmatter, content, filename, and optionally manifest.
    """
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    old_id = args.old_id.upper()

    try:
        parse_task_id(old_id)
        new_epic, new_number = parse_task_id(args.new_id.upper())
    except ValueError as exc:
        print_error(str(exc))
        sys.exit(1)

    target_id = make_task_id(new_epic, new_number)

    result = find_task_file(old_id)
    if not result:
        print_error(f"Task not found: {args.old_id}")
        sys.exit(1)
    old_path, current_status = result

    existing_new = find_task_file(target_id)
    if existing_new and not args.force:
        print_error(f"Task {target_id} already exists")
        print_info("Use --force to overwrite")
        sys.exit(1)

    if existing_new and args.force:
        existing_new[0].unlink()

    task = load_task(old_id)
    task.id = target_id
    task.epic = new_epic
    task.number = new_number

    pattern = r"\b" + re.escape(old_id) + r"\b"
    task.content = re.sub(pattern, task.id, task.content, flags=re.MULTILINE)

    old_path.unlink()

    if not args.skip_manifest:
        remove_manifest_entry(old_id)

    write_task(task, update_manifest=not args.skip_manifest)

    print_success(f"Renamed {old_id} → {task.id}")
    print_info(f"File moved: {current_status}/{task.id}.md")


__all__ = ['cmd_rename']
