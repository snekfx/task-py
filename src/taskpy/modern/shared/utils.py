"""Shared utility functions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

from taskpy.legacy.models import HistoryEntry, Task, TaskStatus
from taskpy.legacy.output import print_error
from taskpy.legacy.storage import TaskStorage


def require_initialized(storage: TaskStorage):
    """Exit with helpful message if storage isn't initialized."""
    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)


def load_task_or_exit(storage: TaskStorage, task_id: str) -> tuple[Task, Path, TaskStatus]:
    """Return (task, path, status) or exit with error if not found/readable."""
    result = storage.find_task_file(task_id)
    if not result:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    path, status = result
    try:
        task = storage.read_task_file(path)
    except Exception as exc:  # pragma: no cover - surfaced by existing tests
        print_error(f"Failed to read task {task_id}: {exc}")
        sys.exit(1)

    return task, path, status


def format_history_entry(entry: HistoryEntry) -> List[str]:
    """Return formatted lines for a single history entry."""
    local_time = entry.timestamp.astimezone()
    timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")

    if entry.from_status and entry.to_status:
        transition = f"{entry.from_status} → {entry.to_status}"
        action_display = f"{entry.action}: {transition}"
    else:
        action_display = entry.action

    lines = [f"  [{timestamp}] {action_display}"]
    if entry.reason:
        lines.append(f"    Reason: {entry.reason}")
    if entry.actor:
        lines.append(f"    Actor: {entry.actor}")
    if entry.metadata:
        for key, value in entry.metadata.items():
            lines.append(f"    {key}: {value}")
    return lines


def add_reason_argument(parser, *, required: bool, help_text: str):
    """Add a --reason flag with consistent help text."""
    parser.add_argument(
        '--reason',
        required=required,
        help=help_text,
    )
    return parser


__all__ = [
    "add_reason_argument",
    "format_history_entry",
    "load_task_or_exit",
    "require_initialized",
]
