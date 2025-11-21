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


def format_history_entry(entry) -> List[str]:
    """Return formatted lines for a single history entry.

    Handles both dict-based entries (modern) and HistoryEntry objects (legacy).
    """
    from datetime import datetime

    # Support both dict and object formats
    if isinstance(entry, dict):
        timestamp_str = entry.get("timestamp", "")
        # Parse ISO format timestamp string to datetime
        if isinstance(timestamp_str, str):
            timestamp_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp_dt = timestamp_str
        local_time = timestamp_dt.astimezone()
        timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")

        from_status = entry.get("from_status")
        to_status = entry.get("to_status")
        action = entry.get("action", "")
        reason = entry.get("reason")
        actor = entry.get("actor")
        metadata = entry.get("metadata")
    else:
        # Legacy HistoryEntry object
        local_time = entry.timestamp.astimezone()
        timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S")
        from_status = entry.from_status
        to_status = entry.to_status
        action = entry.action
        reason = entry.reason
        actor = entry.actor
        metadata = entry.metadata

    if from_status and to_status:
        transition = f"{from_status} → {to_status}"
        action_display = f"{action}: {transition}"
    else:
        action_display = action

    lines = [f"  [{timestamp}] {action_display}"]
    if reason:
        lines.append(f"    Reason: {reason}")
    if actor:
        lines.append(f"    Actor: {actor}")
    if metadata:
        for key, value in metadata.items():
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
