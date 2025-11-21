"""Command implementations for signoff list management."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import List

from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.shared.config import (
    add_signoff_tickets,
    load_signoff_list,
    remove_signoff_tickets,
)
from taskpy.modern.shared.utils import require_initialized


def _parse_task_ids(raw_ids: List[str]) -> List[str]:
    """Parse comma/space separated task IDs."""
    ids: List[str] = []
    for item in raw_ids:
        if "," in item:
            ids.extend([p.strip().upper() for p in item.split(",") if p.strip()])
        else:
            ids.append(item.strip().upper())
    # dedupe preserving order
    seen = set()
    return [tid for tid in ids if tid not in seen and not seen.add(tid)]


def cmd_signoff(args: Namespace):
    """Entry point for `taskpy signoff`."""
    storage = TaskStorage(Path.cwd())
    require_initialized(storage)

    action = getattr(args, "signoff_action", "list")

    if action == "list":
        tickets = load_signoff_list(storage.root)
        if not tickets:
            print_info("No tickets in signoff list")
        else:
            print_success("Signoff tickets", "Signoff")
            for tid in tickets:
                print(f"  • {tid}")
        return

    raw_ids = getattr(args, "task_ids", []) or []
    task_ids = _parse_task_ids(raw_ids)
    if not task_ids:
        print_error("No task IDs provided")
        raise SystemExit(1)

    if action == "add":
        updated = add_signoff_tickets(task_ids, storage.root)
        print_success(f"Added {len(task_ids)} ticket(s) to signoff list", "Signoff Updated")
        for tid in task_ids:
            print(f"  ✓ {tid}")
        print_info(f"Total signoff tickets: {len(updated)}")
    elif action == "remove":
        updated = remove_signoff_tickets(task_ids, storage.root)
        print_success(f"Removed {len(task_ids)} ticket(s) from signoff list", "Signoff Updated")
        for tid in task_ids:
            print(f"  ✗ {tid}")
        print_info(f"Total signoff tickets: {len(updated)}")
    else:  # pragma: no cover - parser should guard
        print_error(f"Unknown signoff action: {action}")
        raise SystemExit(1)


__all__ = ["cmd_signoff"]
