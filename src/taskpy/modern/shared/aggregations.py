"""Shared aggregation helpers for TaskPy manifest data."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence

ManifestRow = Dict[str, Any]

STATUS_ORDER = [
    "stub",
    "backlog",
    "ready",
    "active",
    "qa",
    "regression",
    "done",
    "archived",
    "blocked",
]

PRIORITY_ORDER = ["critical", "high", "medium", "low"]


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def count_by_status(rows: Iterable[ManifestRow]) -> Dict[str, int]:
    return _count_by_field(rows, "status", default_value="unknown")


def count_by_priority(rows: Iterable[ManifestRow]) -> Dict[str, int]:
    return _count_by_field(rows, "priority", default_value="unknown")


def count_by_epic(rows: Iterable[ManifestRow]) -> Dict[str, int]:
    return _count_by_field(rows, "epic", default_value="unknown")


def _count_by_field(
    rows: Iterable[ManifestRow], field: str, default_value: str = "unknown"
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = row.get(field) or default_value
        counts[value] = counts.get(value, 0) + 1
    return counts


def sum_story_points(rows: Iterable[ManifestRow]) -> int:
    return sum(_as_int(row.get("story_points")) for row in rows)


def sum_story_points_by_status(rows: Iterable[ManifestRow]) -> Dict[str, int]:
    totals: Dict[str, int] = defaultdict(int)
    for row in rows:
        status = row.get("status", "unknown")
        totals[status] += _as_int(row.get("story_points"))
    return dict(totals)


def filter_by_status(rows: Iterable[ManifestRow], status: str) -> List[ManifestRow]:
    status_normalized = (status or "").lower()
    return [
        row
        for row in rows
        if row.get("status", "").lower() == status_normalized
    ]


def filter_by_statuses(
    rows: Iterable[ManifestRow], statuses: Sequence[str]
) -> List[ManifestRow]:
    normalized = {status.lower() for status in statuses}
    return [
        row
        for row in rows
        if row.get("status", "").lower() in normalized
    ]


def filter_by_sprint(
    rows: Iterable[ManifestRow], in_sprint: bool = True
) -> List[ManifestRow]:
    target = "true" if in_sprint else "false"
    return [
        row
        for row in rows
        if str(row.get("in_sprint", "false")).lower() == target
    ]


def filter_by_milestone(
    rows: Iterable[ManifestRow], milestone_id: str
) -> List[ManifestRow]:
    milestone_id = milestone_id or ""
    return [
        row
        for row in rows
        if (row.get("milestone") or "") == milestone_id
    ]


def filter_by_epic(rows: Iterable[ManifestRow], epic: str) -> List[ManifestRow]:
    epic = (epic or "").upper()
    return [
        row
        for row in rows
        if (row.get("epic") or "").upper() == epic
    ]


def get_project_stats(rows: Sequence[ManifestRow]) -> Dict[str, Any]:
    return {
        "total_tasks": len(rows),
        "total_story_points": sum_story_points(rows),
        "by_status": count_by_status(rows),
        "by_priority": count_by_priority(rows),
    }


def get_sprint_stats(rows: Sequence[ManifestRow]) -> Dict[str, Any]:
    stats = get_project_stats(rows)
    stats["by_status"] = _ensure_order(stats["by_status"], STATUS_ORDER)
    stats["by_priority"] = _ensure_order(stats["by_priority"], PRIORITY_ORDER)
    return stats


def get_milestone_stats(rows: Sequence[ManifestRow]) -> Dict[str, Any]:
    completed_rows = [
        row for row in rows if row.get("status") in {"done", "archived"}
    ]
    total_sp = sum_story_points(rows)
    completed_sp = sum_story_points(completed_rows)
    return {
        "total_tasks": len(rows),
        "completed_tasks": len(completed_rows),
        "story_points_total": total_sp,
        "story_points_completed": completed_sp,
        "story_points_remaining": max(total_sp - completed_sp, 0),
        "by_status": count_by_status(rows),
    }


def _ensure_order(counts: Dict[str, int], order: Sequence[str]) -> Dict[str, int]:
    """Return counts with keys ordered, ensuring missing keys default to 0."""
    ordered: Dict[str, int] = {}
    for key in order:
        if key in counts:
            ordered[key] = counts[key]
    for key, value in counts.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


__all__ = [
    "count_by_status",
    "count_by_priority",
    "count_by_epic",
    "filter_by_epic",
    "filter_by_milestone",
    "filter_by_sprint",
    "filter_by_status",
    "filter_by_statuses",
    "get_milestone_stats",
    "get_project_stats",
    "get_sprint_stats",
    "sum_story_points",
    "sum_story_points_by_status",
]
