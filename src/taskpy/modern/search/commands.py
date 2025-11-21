"""Search command implementation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Iterable, List

from taskpy.legacy.output import print_error, print_success
from taskpy.modern.shared.output import get_output_mode, OutputMode
from taskpy.modern.shared.tasks import KanbanNotInitialized, load_manifest, load_task
from taskpy.modern.views import ListView, ColumnConfig


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [v.strip().lower() for v in value.split(",") if v.strip()]


def _task_fields(task_row: Dict[str, str], include_body: bool) -> Dict[str, str]:
    fields = {
        "id": task_row.get("id", ""),
        "title": task_row.get("title", ""),
        "tags": task_row.get("tags", ""),
        "status": task_row.get("status", ""),
        "epic": task_row.get("epic", ""),
    }
    if include_body:
        try:
            task = load_task(task_row["id"], Path.cwd())
            fields["body"] = task.content or ""
        except FileNotFoundError:
            fields["body"] = ""
    return fields


def _matches(task_fields: Dict[str, str], filters: Iterable[str], keywords: List[str]) -> bool:
    """Return True if all keywords are found in any of the selected fields."""
    for kw in keywords:
        kw = kw.lower()
        found = any(kw in task_fields.get(f, "").lower() for f in filters)
        if not found:
            return False
    return True


def cmd_search(args):
    """Search tasks by keyword/tag with optional filters."""
    try:
        rows = load_manifest(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    keywords = [kw.lower() for kw in getattr(args, "keywords", []) if kw.strip()]
    if not keywords:
        print_error("No keywords provided")
        sys.exit(1)

    filters = _parse_csv(getattr(args, "filters", None)) or ["title", "body", "tags"]
    valid_filters = {"title", "body", "tags", "id", "epic", "status"}
    invalid = [f for f in filters if f not in valid_filters]
    if invalid:
        print_error(f"Invalid filters: {', '.join(invalid)}")
        sys.exit(1)

    status_filter = set(_parse_csv(getattr(args, "status", None)))
    include_archived = bool(getattr(args, "archived", False))
    epic_filter = getattr(args, "epic", None)
    in_sprint_only = bool(getattr(args, "in_sprint", False))

    results = []
    for row in rows:
        status = row.get("status", "").lower()

        if status_filter and status not in status_filter:
            continue
        if not include_archived and status == "archived":
            continue
        if epic_filter and row.get("epic", "").upper() != epic_filter.upper():
            continue
        if in_sprint_only and row.get("in_sprint", "false") != "true":
            continue

        fields = _task_fields(row, include_body="body" in filters)
        if _matches(fields, filters, keywords):
            tags_list = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
            results.append(
                {
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "status": row.get("status", ""),
                    "story_points": int(row.get("story_points", 0) or 0),
                    "tags": tags_list,
                    "priority": row.get("priority", ""),
                    "in_sprint": row.get("in_sprint", "false"),
                }
            )

    mode = get_output_mode()
    if mode == OutputMode.AGENT:
        payload = {
            "count": len(results),
            "items": results,
            "filters": {
                "keywords": keywords,
                "fields": filters,
                "status": list(status_filter) if status_filter else None,
                "epic": epic_filter,
                "in_sprint": in_sprint_only,
                "include_archived": include_archived,
            },
        }
        import json
        print(json.dumps(payload, indent=2))
        return

    if mode == OutputMode.DATA:
        print_success(f"Found {len(results)} task(s)")
        for task in results:
            tags = f" | tags: {', '.join(task['tags'])}" if task['tags'] else ""
            sprint = "[SPRINT] " if task.get("in_sprint", "false") == "true" else ""
            print(f"{sprint}{task['id']}: {task['title']} [{task['status']}] SP={task['story_points']}{tags}")
        return

    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field="title"),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Tags", field=lambda t: ", ".join(t.get("tags", []))),
    ]

    view = ListView(
        data=results,
        columns=columns,
        title=f"Search Results ({len(results)} task(s))",
        output_mode=mode,
        status_field="status",
    )
    if not results:
        print_success("No tasks matched the search")
        return
    view.display()
