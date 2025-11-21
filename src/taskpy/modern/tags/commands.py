"""Tags command implementations."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import List

from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.shared.utils import require_initialized
from taskpy.modern.workflow.commands import parse_task_ids


def _parse_tags(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _display_tags(task_id: str, tags: List[str]):
    joined = ", ".join(tags) if tags else "(none)"
    print(f"{task_id}: {joined}")


def cmd_tags(args: Namespace):
    """List or update tags on one or more tasks."""
    storage = TaskStorage(Path.cwd())
    require_initialized(storage)

    task_ids = parse_task_ids(getattr(args, "task_ids", []) or [])
    if not task_ids:
        print_error("No valid task IDs provided")
        raise SystemExit(1)

    add_tags = _parse_tags(getattr(args, "add", None))
    remove_tags = _parse_tags(getattr(args, "remove", None))
    set_tags = _parse_tags(getattr(args, "set_tags", None))
    clear = bool(getattr(args, "clear", False))
    list_only = bool(getattr(args, "list", False)) or (not add_tags and not remove_tags and not set_tags and not clear)

    updated_any = False

    for tid in task_ids:
        found = storage.find_task_file(tid)
        if not found:
            print_error(f"Task not found: {tid}")
            raise SystemExit(1)

        path, _ = found
        task = storage.read_task_file(path)

        if clear:
            task.tags = []
            updated_any = True
        elif set_tags:
            task.tags = set_tags.copy()
            updated_any = True
        else:
            if add_tags:
                existing = set(task.tags or [])
                for tag in add_tags:
                    if tag not in existing:
                        task.tags.append(tag)
                        existing.add(tag)
                        updated_any = True
            if remove_tags and task.tags:
                before = len(task.tags)
                task.tags = [t for t in task.tags if t not in remove_tags]
                if len(task.tags) != before:
                    updated_any = True

        if updated_any and not list_only:
            storage.write_task_file(task)

        # Always display tags
        _display_tags(task.id, task.tags)

    if updated_any and not list_only:
        storage.rebuild_manifest()
        print_success("Updated tags and rebuilt manifest", "Tags Updated")


__all__ = ["cmd_tags"]
