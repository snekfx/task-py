"""Edit operations for core task management."""

import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error
from taskpy.modern.shared.tasks import KanbanNotInitialized, ensure_initialized, find_task_file, open_in_editor


def cmd_edit(args):
    """Edit a task in $EDITOR."""
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
    try:
        _open_in_editor(path)
    except RuntimeError as exc:
        print_error(str(exc))
        sys.exit(1)


__all__ = ['cmd_edit']

# Backwards compatibility for tests expecting legacy helper
_open_in_editor = open_in_editor
