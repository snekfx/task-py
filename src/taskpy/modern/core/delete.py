"""Delete command implementation for the modern core module."""

import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_info, print_success
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    find_task_file,
    load_task,
    write_task,
    remove_manifest_entry,
    get_trash_dir,
    get_manifest_row,
    next_auto_id,
    utc_now,
)


def _resolve_auto_id(task_id: str) -> int:
    """Ensure tasks getting deleted have an auto_id."""
    row = get_manifest_row(task_id)
    if row and row.get("auto_id"):
        try:
            return int(row["auto_id"])
        except ValueError:
            pass
    return next_auto_id()


def cmd_delete(args):
    """Move a task into the trash directory (soft delete)."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_id = args.task_id.upper()
    reason = getattr(args, "reason", "").strip()
    if not reason:
        print_error("--reason is required for delete")
        sys.exit(1)

    located = find_task_file(task_id)
    if not located:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    task = load_task(task_id)
    if task.auto_id is None:
        task.auto_id = _resolve_auto_id(task_id)
        print_info(f"Assigned auto_id={task.auto_id} to {task_id}", "Auto ID")

    history_entry = {
        "timestamp": utc_now().isoformat(),
        "action": "delete",
        "from_status": task.status,
        "to_status": "trash",
        "reason": reason,
    }
    task.history.append(history_entry)

    try:
        write_task(task, update_manifest=False)
    except Exception as exc:  # pragma: no cover - defensive (write failures)
        print_error(f"Failed to update task before delete: {exc}")
        sys.exit(1)

    remove_manifest_entry(task.id)

    path, _ = located
    trash_dir = get_trash_dir()
    trash_path = trash_dir / f"{task.auto_id}.{task.id}.md"

    if trash_path.exists():
        print_error(
            f"Trash entry already exists for auto_id {task.auto_id}. "
            "Recover or empty trash first."
        )
        sys.exit(1)

    try:
        path.replace(trash_path)
    except Exception as exc:  # pragma: no cover - filesystem failures
        print_error(f"Failed to move task to trash: {exc}")
        sys.exit(1)

    print_success(f"Deleted {task.id} (moved to trash)", "Task Deleted")
    print_info(f"Recover with: taskpy recover {task.auto_id}")


__all__ = ["cmd_delete"]
