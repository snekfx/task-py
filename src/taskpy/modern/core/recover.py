"""Recover command implementation for the modern core module."""

import re
import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_info, print_success
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    ensure_initialized,
    find_task_file,
    find_trash_file,
    get_manifest_row,
    load_task_from_path,
    make_task_id,
    next_task_number,
    write_task,
    utc_now,
)


def _task_id_in_use(task_id: str) -> bool:
    """Return True if a task ID currently exists on disk or in manifest."""
    if find_task_file(task_id):
        return True
    row = get_manifest_row(task_id)
    return row is not None


def _assign_new_id(task, root: Path) -> tuple[str, int, bool]:
    """Determine a safe task ID when conflicts occur."""
    desired_id = task.id
    epic = task.epic
    number = task.number

    if not _task_id_in_use(desired_id):
        return desired_id, number, False

    next_number = max(number + 1, next_task_number(epic, root))
    while next_number <= 999:
        candidate_id = make_task_id(epic, next_number)
        if not _task_id_in_use(candidate_id):
            return candidate_id, next_number, True
        next_number += 1

    print_error("No available task IDs remaining in this epic (limit 999).")
    sys.exit(1)


def cmd_recover(args):
    """Recover a task from trash back into the kanban."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    reason = getattr(args, "reason", "").strip()
    if not reason:
        print_error("--reason is required for recover")
        sys.exit(1)

    auto_id = args.auto_id
    trash_path = find_trash_file(auto_id)
    if not trash_path:
        print_error(f"No trashed task found with auto_id {auto_id}")
        sys.exit(1)

    try:
        task = load_task_from_path(trash_path)
    except Exception as exc:
        print_error(f"Failed to load trashed task: {exc}")
        sys.exit(1)

    original_id = task.id
    new_id, new_number, changed = _assign_new_id(task, Path.cwd())

    if changed:
        task.id = new_id
        task.number = new_number
        pattern = r"\b" + re.escape(original_id) + r"\b"
        task.content = re.sub(pattern, task.id, task.content, flags=re.MULTILINE)

    history_entry = {
        "timestamp": utc_now().isoformat(),
        "action": "recover",
        "from_status": "trash",
        "to_status": task.status,
        "reason": reason,
        "metadata": {
            "from_id": original_id,
            "to_id": task.id,
        },
    }
    task.history.append(history_entry)

    try:
        write_task(task)
        trash_path.unlink()
    except Exception as exc:  # pragma: no cover - filesystem failures
        print_error(f"Failed to recover task: {exc}")
        sys.exit(1)

    if changed:
        print_success(
            f"Recovered as {task.id} (was {original_id})",
            "Task Recovered",
        )
    else:
        print_success(f"Recovered {task.id}", "Task Recovered")
    print_info(f"Auto ID: {task.auto_id} (reason recorded)")


__all__ = ["cmd_recover"]
