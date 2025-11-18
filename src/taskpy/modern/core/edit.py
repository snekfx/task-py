"""Edit operations for core task management."""

import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error
from taskpy.legacy.commands import _open_in_editor


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def cmd_edit(args):
    """Edit a task in $EDITOR."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result
    _open_in_editor(path)


__all__ = ['cmd_edit']
