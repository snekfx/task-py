"""Archive command implementation with signoff gating."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

from taskpy.legacy.models import HistoryEntry, TaskStatus, utc_now
from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.shared.config import (
    is_feature_enabled,
    load_signoff_list,
    remove_signoff_tickets,
)
from taskpy.modern.shared.utils import require_initialized


def _parse_task_ids(raw_ids: List[str]) -> List[str]:
    ids: List[str] = []
    for item in raw_ids:
        if "," in item:
            ids.extend([p.strip().upper() for p in item.split(",") if p.strip()])
        else:
            ids.append(item.strip().upper())
    seen = set()
    return [tid for tid in ids if tid not in seen and not seen.add(tid)]


def _collect_done_tasks(storage: TaskStorage) -> List[Tuple[str, Path]]:
    done_dir = storage.status_dir / TaskStatus.DONE.value
    results: List[Tuple[str, Path]] = []
    for path in sorted(done_dir.glob("*.md")):
        task_id = path.stem.upper()
        results.append((task_id, path))
    return results


def _load_tasks(storage: TaskStorage, task_ids: List[str]) -> List[Tuple[str, Path]]:
    tasks = []
    for tid in task_ids:
        found = storage.find_task_file(tid)
        if not found:
            print_error(f"Task not found: {tid}")
            sys.exit(1)
        path, status = found
        if status != TaskStatus.DONE:
            print_error(f"{tid} is not in done status (status={status.value})")
            sys.exit(1)
        tasks.append((tid, path))
    return tasks


def _confirm_bulk(task_ids: List[str], auto_confirm: bool) -> bool:
    if auto_confirm or len(task_ids) <= 1:
        return True
    response = input(f"Archive {len(task_ids)} task(s)? [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def cmd_archive(args):
    storage = TaskStorage(Path.cwd())
    require_initialized(storage)

    if not getattr(args, "signoff", False):
        print_error("--signoff flag is required to archive tasks")
        sys.exit(1)

    signoff_mode = is_feature_enabled("signoff_mode", storage.root)
    signoff_list = set(load_signoff_list(storage.root))
    reason = (getattr(args, "reason", "") or "").strip()

    # Determine target tasks
    targets: List[Tuple[str, Path]] = []
    if getattr(args, "all_done", False):
        targets = _collect_done_tasks(storage)
        if not targets:
            print_info("No done tasks to archive")
            return
    else:
        raw_ids = getattr(args, "task_ids", []) or []
        task_ids = _parse_task_ids(raw_ids)
        if not task_ids:
            print_error("Provide task IDs or use --all-done to archive all done tasks")
            sys.exit(1)
        targets = _load_tasks(storage, task_ids)

    # Gating
    blocked = []
    for tid, _ in targets:
        if signoff_mode and tid not in signoff_list:
            blocked.append(f"{tid}: not in signoff list (signoff_mode enabled)")
        elif not signoff_mode and tid not in signoff_list and not reason:
            blocked.append(f"{tid}: provide --reason when not signed off (signoff_mode disabled)")
    if blocked:
        print_error("Cannot archive:")
        for msg in blocked:
            print(f"  • {msg}")
        sys.exit(1)

    if getattr(args, "dry_run", False):
        print_info("Dry-run: tasks that would be archived:")
        for tid, _ in targets:
            print(f"  • {tid}")
        return

    if not _confirm_bulk([tid for tid, _ in targets], getattr(args, "yes", False)):
        print_info("Archive cancelled")
        return

    removed_from_signoff: List[str] = []

    for tid, path in targets:
        task = storage.read_task_file(path)
        task.status = TaskStatus.ARCHIVED
        metadata = {
            "signoff_mode": signoff_mode,
            "signoff_listed": tid in signoff_list,
        }
        if reason:
            metadata["reason"] = reason
        history_entry = HistoryEntry(
            timestamp=utc_now(),
            action="archive",
            from_status=TaskStatus.DONE.value,
            to_status=TaskStatus.ARCHIVED.value,
            reason=reason or None,
            metadata=metadata,
        )
        task.history.append(history_entry)

        try:
            path.unlink()
        except FileNotFoundError:
            pass
        storage.write_task_file(task)
        removed_from_signoff.append(tid)
        print_success(f"Archived {tid}")

    # Clean up signoff list for archived tasks
    if removed_from_signoff and signoff_list:
        remaining = signoff_list.difference(removed_from_signoff)
        remove_signoff_tickets(removed_from_signoff, storage.root)
        if remaining != signoff_list:
            print_info(f"Removed {len(removed_from_signoff)} archived task(s) from signoff list")

    # Rebuild manifest after archival changes
    try:
        storage.rebuild_manifest()
        print_info("Manifest rebuilt after archival")
    except Exception as exc:  # pragma: no cover - defensive
        print_error(f"Failed to rebuild manifest: {exc}")


__all__ = ["cmd_archive"]
