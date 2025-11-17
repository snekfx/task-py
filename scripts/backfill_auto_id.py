#!/usr/bin/env python3
"""
Backfill auto_id for existing tasks based on created timestamp.

This script assigns auto_id values to tasks that don't have them,
using their creation timestamp for chronological ordering.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from taskpy.storage import TaskStorage
from taskpy.models import TaskStatus

def main():
    """Backfill auto_id for all existing tasks."""
    root = Path.cwd()
    storage = TaskStorage(root)

    if not storage.is_initialized():
        print("Error: TaskPy not initialized")
        sys.exit(1)

    # Collect all tasks across all statuses
    all_tasks = []
    for status in TaskStatus:
        status_dir = storage.status_dir / status.value
        if not status_dir.exists():
            continue

        for task_file in sorted(status_dir.glob('*.md')):
            try:
                task = storage.read_task_file(task_file)
                all_tasks.append((task, task_file))
            except Exception as e:
                print(f"Warning: Failed to read {task_file}: {e}")

    if not all_tasks:
        print("No tasks found")
        return

    # Sort by created timestamp (chronological order)
    # Handle both timezone-aware and naive datetimes
    def get_sort_key(task_tuple):
        task = task_tuple[0]
        created = task.created
        # Convert naive datetime to comparable timestamp
        if created.tzinfo is None:
            return created.timestamp()
        else:
            return created.timestamp()

    all_tasks.sort(key=get_sort_key)

    # Assign auto_id in chronological order
    next_auto_id = 1
    updated_count = 0

    for task, task_file in all_tasks:
        if task.auto_id is None:
            task.auto_id = next_auto_id
            storage.write_task_file(task)
            print(f"✓ {task.id}: auto_id={next_auto_id}")
            updated_count += 1
        else:
            print(f"- {task.id}: already has auto_id={task.auto_id}")
        next_auto_id += 1

    # Update sequence counter to next value
    storage.sequence_file.write_text(f"{next_auto_id}\n")

    print(f"\n✓ Backfilled {updated_count} tasks")
    print(f"✓ Sequence counter set to {next_auto_id}")
    print(f"\nRun: taskpy manifest rebuild")

if __name__ == "__main__":
    main()
