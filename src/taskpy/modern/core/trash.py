"""Trash management commands for the modern core module."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from taskpy.modern.shared.messages import print_error, print_info, print_success
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    get_trash_dir,
    load_task_from_path,
)
from taskpy.modern.views import ListView, ColumnConfig


def _format_timestamp(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def _find_latest_action(history: List[Dict[str, object]], action: str) -> Dict[str, object]:
    for entry in reversed(history or []):
        if isinstance(entry, dict) and entry.get("action") == action:
            return entry
    return {}


def _collect_trash_entries(root: Path) -> List[Dict[str, str]]:
    trash_dir = get_trash_dir(root)
    entries: List[Dict[str, str]] = []
    for path in sorted(trash_dir.glob("*.md")):
        name = path.name
        if "." not in name:
            continue
        prefix, remainder = name.split(".", 1)
        if not prefix.isdigit():
            continue
        auto_id = prefix
        task_id = remainder[:-3] if remainder.endswith(".md") else remainder
        history_data: Dict[str, object] = {}
        try:
            task = load_task_from_path(path)
            history_data = _find_latest_action(task.history, "delete")
            deleted_raw = history_data.get("timestamp", "")
            reason = history_data.get("reason", "")
            deleted_display = _format_timestamp(deleted_raw) if deleted_raw else ""
        except Exception:
            task = None
            reason = ""
            deleted_display = ""
        title = task.title if task else "(invalid task file)"
        entries.append(
            {
                "auto_id": auto_id,
                "task_id": task_id,
                "title": title,
                "deleted": deleted_display,
                "reason": reason,
                "_sort": history_data.get("timestamp", ""),
            }
        )
    entries.sort(key=lambda row: row.get("_sort", ""), reverse=True)
    return entries


def _empty_trash(root: Path):
    trash_dir = get_trash_dir(root)
    files = [p for p in trash_dir.glob("*.md") if p.is_file()]
    if not files:
        print_info("Trash bin already empty")
        return

    confirmation = input(
        f"Permanently delete {len(files)} tasks from trash? (y/N) "
    ).strip().lower()
    if confirmation not in {"y", "yes"}:
        print_info("Trash empty cancelled")
        return

    for path in files:
        path.unlink()

    print_success(f"Permanently deleted {len(files)} tasks", "Trash Emptied")


def cmd_trash(args):
    """List trashed tasks or empty the trash bin."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    action = getattr(args, "action", None)
    if action == "empty":
        _empty_trash(Path.cwd())
        return

    entries = _collect_trash_entries(Path.cwd())
    if not entries:
        print_info("Trash bin is empty")
        return

    for entry in entries:
        entry.pop("_sort", None)

    view = ListView(
        data=entries,
        columns=[
            ColumnConfig(name="Auto ID", field="auto_id"),
            ColumnConfig(name="Task ID", field="task_id"),
            ColumnConfig(name="Title", field="title"),
            ColumnConfig(name="Deleted", field="deleted"),
            ColumnConfig(name="Reason", field="reason"),
        ],
        title=f"Trash ({len(entries)} tasks)",
        output_mode=get_output_mode(),
        grey_done=False,
    )
    view.display()


__all__ = ["cmd_trash"]
