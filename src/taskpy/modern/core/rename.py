"""Rename operations for core task management."""

import re
import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.models import Task, TaskStatus, utc_now


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def cmd_rename(args):
    """
    Rename a task's ID (epic and/or number).
    Updates frontmatter, content, filename, and optionally manifest.
    """
    storage = get_storage()

    # Parse old and new IDs
    try:
        old_epic, old_number = Task.parse_task_id(args.old_id)
        new_epic, new_number = Task.parse_task_id(args.new_id)
    except ValueError as e:
        print_error(f"Invalid task ID format: {e}")
        sys.exit(1)

    # Find old task
    result = storage.find_task_file(args.old_id)
    if not result:
        print_error(f"Task not found: {args.old_id}")
        sys.exit(1)

    old_path, current_status = result

    # Check if new ID already exists (unless force)
    if not args.force:
        new_result = storage.find_task_file(args.new_id)
        if new_result:
            print_error(f"Task {args.new_id} already exists")
            print_info("Use --force to overwrite")
            sys.exit(1)

    # Read task
    task = storage.read_task_file(old_path)

    # Update task fields
    task.id = args.new_id
    task.epic = new_epic
    task.number = new_number
    task.updated = utc_now()

    # Read the markdown content to update ID references
    with open(old_path, 'r') as f:
        content = f.read()

    # Replace old ID with new ID in content (using word boundaries for safety)
    # Match the old ID but not as part of a longer word
    pattern = r'\b' + re.escape(args.old_id) + r'\b'
    updated_content = re.sub(pattern, args.new_id, content)

    # Write task to new location
    new_path = storage.status_dir / current_status.value / f"{args.new_id}.md"

    # Write the updated content directly (includes frontmatter changes from task object)
    storage.write_task_file(task)

    # If we need to update content beyond what write_task_file does
    # Re-read and update content sections
    with open(new_path, 'r') as f:
        final_content = f.read()

    # Replace ID in the body (after frontmatter)
    parts = final_content.split('---\n', 2)
    if len(parts) == 3:
        frontmatter_start, frontmatter_body, markdown_body = parts
        # Update markdown body
        pattern = r'\b' + re.escape(args.old_id) + r'\b'
        updated_body = re.sub(pattern, args.new_id, markdown_body)
        final_content = f"---\n{frontmatter_body}---\n{updated_body}"

        with open(new_path, 'w') as f:
            f.write(final_content)

    # Delete old file
    old_path.unlink()

    # Update manifest (unless skip flag)
    if not args.skip_manifest:
        # Rebuild manifest to pick up the rename
        storage.rebuild_manifest()

    print_success(f"Renamed {args.old_id} → {args.new_id}")
    if current_status != TaskStatus.STUB:
        print_info(f"File moved: {current_status.value}/{args.new_id}.md")


__all__ = ['cmd_rename']
