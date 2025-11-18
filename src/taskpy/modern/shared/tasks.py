"""
Helpers for reading and manipulating TaskPy kanban data without legacy storage.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

KANBAN_RELATIVE_PATH = Path("data/kanban")
MANIFEST_FILENAME = "manifest.tsv"
STATUS_FOLDERS = [
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


class KanbanNotInitialized(Exception):
    """Raised when TaskPy data directory is missing."""


@dataclass
class TaskRecord:
    """Represents a parsed task markdown file."""

    id: str
    title: str
    epic: str
    number: int
    status: str
    priority: str
    story_points: int
    created: datetime
    updated: datetime
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    assigned: Optional[str] = None
    milestone: Optional[str] = None
    blocked_reason: Optional[str] = None
    in_sprint: bool = False
    commit_hash: Optional[str] = None
    demotion_reason: Optional[str] = None
    resolution: Optional[str] = None
    resolution_reason: Optional[str] = None
    duplicate_of: Optional[str] = None
    auto_id: Optional[int] = None
    nfrs: List[str] = field(default_factory=list)
    references: Dict[str, List[str]] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    content: str = ""


def _kanban_paths(root: Optional[Path] = None) -> Tuple[Path, Path]:
    base = Path.cwd() if root is None else root
    kanban = base / KANBAN_RELATIVE_PATH
    manifest = kanban / MANIFEST_FILENAME
    if not manifest.exists():
        raise KanbanNotInitialized(
            "TaskPy data directory not found. Run `taskpy init` in this project."
        )
    return kanban, manifest


def load_manifest(root: Optional[Path] = None) -> List[Dict[str, str]]:
    """Read manifest.tsv and return a list of dictionaries."""
    _, manifest = _kanban_paths(root)
    with manifest.open("r", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader]


def format_title(title: str, width: int = 70) -> str:
    """Truncate titles for ListView display."""
    if len(title) <= width:
        return title
    return f"{title[:width-3]}..."


def sort_manifest_rows(rows: List[Dict[str, str]], mode: str) -> List[Dict[str, str]]:
    """Sort manifest rows using supported modes."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_order = {
        "stub": 0,
        "backlog": 1,
        "ready": 2,
        "active": 3,
        "qa": 4,
        "regression": 5,
        "done": 6,
        "archived": 7,
        "blocked": 8,
    }

    def as_int(row: Dict[str, str], key: str) -> int:
        try:
            return int(row.get(key, 0))
        except (ValueError, TypeError):
            return 0

    if mode == "priority":
        key_fn = lambda r: priority_order.get(r.get("priority", "").lower(), 99)
    elif mode == "status":
        key_fn = lambda r: status_order.get(r.get("status", "").lower(), 99)
    elif mode == "sp":
        key_fn = lambda r: as_int(r, "story_points")
    elif mode == "created":
        key_fn = lambda r: r.get("created", "")
    elif mode == "updated":
        key_fn = lambda r: r.get("updated", "")
    else:
        return rows

    reverse = mode in {"sp", "created", "updated"}
    return sorted(rows, key=key_fn, reverse=reverse)


def parse_task_ids(raw_ids: List[str]) -> List[str]:
    """Normalize comma/space separated task IDs."""
    task_ids: List[str] = []
    for item in raw_ids:
        if "," in item:
            task_ids.extend([part.strip().upper() for part in item.split(",") if part.strip()])
        else:
            task_ids.append(item.strip().upper())

    seen = set()
    ordered: List[str] = []
    for task_id in task_ids:
        if task_id and task_id not in seen:
            ordered.append(task_id)
            seen.add(task_id)
    return ordered


def find_task_file(task_id: str, root: Optional[Path] = None) -> Optional[Tuple[Path, str]]:
    """Locate the markdown file for a task."""
    kanban, _ = _kanban_paths(root)
    status_dir = kanban / "status"
    for status in STATUS_FOLDERS:
        candidate = status_dir / status / f"{task_id}.md"
        if candidate.exists():
            return candidate, status
    # Fallback in case new status directories exist
    for path in status_dir.glob("*/"):
        candidate = path / f"{task_id}.md"
        if candidate.exists():
            return candidate, path.name
    return None


def load_task(task_id: str, root: Optional[Path] = None) -> TaskRecord:
    """Load a single task markdown file into a TaskRecord."""
    found = find_task_file(task_id, root)
    if not found:
        raise FileNotFoundError(f"Task {task_id} not found")
    path, status = found
    record = _read_task_file(path)
    record.status = status
    return record


def _read_task_file(path: Path) -> TaskRecord:
    raw = path.read_text()
    if not raw.startswith("---\n"):
        raise ValueError(f"Invalid task file: {path}")

    end_idx = raw.find("\n---\n", 4)
    if end_idx == -1:
        raise ValueError(f"Invalid task file: {path}")

    frontmatter = raw[4:end_idx]
    body = raw[end_idx + 5 :].strip()
    metadata = yaml.safe_load(frontmatter) or {}

    def _list(value) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        if not value:
            return []
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return []

    def _bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true"
        return False

    def _int(value) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _dt(value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.fromtimestamp(0)

    references = metadata.get("references") or {}
    if not isinstance(references, dict):
        references = {}

    verification = metadata.get("verification") or {}
    if not isinstance(verification, dict):
        verification = {}

    return TaskRecord(
        id=str(metadata.get("id", "")),
        title=str(metadata.get("title", "")),
        epic=str(metadata.get("epic", "")),
        number=int(metadata.get("number", 0)),
        status=str(metadata.get("status", "backlog")),
        priority=str(metadata.get("priority", "medium")),
        story_points=int(metadata.get("story_points", 0)),
        created=_dt(metadata.get("created")),
        updated=_dt(metadata.get("updated")),
        tags=_list(metadata.get("tags")),
        dependencies=_list(metadata.get("dependencies")),
        blocks=_list(metadata.get("blocks")),
        assigned=metadata.get("assigned"),
        milestone=metadata.get("milestone"),
        blocked_reason=metadata.get("blocked_reason"),
        in_sprint=_bool(metadata.get("in_sprint")),
        commit_hash=metadata.get("commit_hash"),
        demotion_reason=metadata.get("demotion_reason"),
        resolution=metadata.get("resolution"),
        resolution_reason=metadata.get("resolution_reason"),
        duplicate_of=metadata.get("duplicate_of"),
        auto_id=_int(metadata.get("auto_id")),
        nfrs=_list(metadata.get("nfrs")),
        references={
            "code": _list(references.get("code")),
            "docs": _list(references.get("docs")),
            "plans": _list(references.get("plans")),
            "tests": _list(references.get("tests")),
        },
        verification={
            "command": verification.get("command"),
            "status": verification.get("status"),
            "last_run": verification.get("last_run"),
            "output": verification.get("output"),
        },
        history=metadata.get("history", []) or [],
        content=body,
    )
