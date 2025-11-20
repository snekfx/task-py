"""
Helpers for reading and manipulating TaskPy kanban data without legacy storage.
"""

from __future__ import annotations

import csv
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib

KANBAN_RELATIVE_PATH = Path("data/kanban")
MANIFEST_FILENAME = "manifest.tsv"
SEQUENCE_FILENAME = ".sequence"
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
VALID_STATUSES = {
    "stub",
    "backlog",
    "ready",
    "active",
    "qa",
    "regression",
    "done",
    "archived",
    "blocked",
}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
TRASH_DIRNAME = "trash"


class KanbanNotInitialized(Exception):
    """Raised when TaskPy data directory is missing."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    created: datetime = field(default_factory=utc_now)
    updated: datetime = field(default_factory=utc_now)
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
    references: Dict[str, List[str]] = field(
        default_factory=lambda: {"code": [], "docs": [], "plans": [], "tests": []}
    )
    verification: Dict[str, Any] = field(
        default_factory=lambda: {"command": None, "status": "pending"}
    )
    history: List[Dict[str, Any]] = field(default_factory=list)
    content: str = ""

    def to_manifest_row(self) -> List[str]:
        return [
            self.id,
            self.epic,
            str(self.number),
            self.status,
            self.title,
            str(self.story_points),
            self.priority,
            self.created.isoformat(),
            self.updated.isoformat(),
            ",".join(self.tags),
            ",".join(self.dependencies),
            ",".join(self.blocks),
            str(self.verification.get("status", "pending")),
            self.assigned or "",
            self.milestone or "",
            self.blocked_reason or "",
            str(self.in_sprint).lower(),
            self.commit_hash or "",
            self.demotion_reason or "",
            str(self.auto_id) if self.auto_id is not None else "",
        ]

    def to_frontmatter_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "epic": self.epic,
            "number": self.number,
            "status": self.status,
            "story_points": self.story_points,
            "priority": self.priority,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "assigned": self.assigned,
            "milestone": self.milestone,
            "blocked_reason": self.blocked_reason,
            "in_sprint": self.in_sprint,
            "commit_hash": self.commit_hash,
            "demotion_reason": self.demotion_reason,
            "resolution": self.resolution,
            "resolution_reason": self.resolution_reason,
            "duplicate_of": self.duplicate_of,
            "auto_id": self.auto_id,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "blocks": self.blocks,
            "nfrs": self.nfrs,
            "references": self.references,
            "verification": self.verification,
            "history": self.history,
        }


def _kanban_paths(root: Optional[Path] = None) -> Tuple[Path, Path]:
    base = Path.cwd() if root is None else root
    kanban = base / KANBAN_RELATIVE_PATH
    manifest = kanban / MANIFEST_FILENAME
    if not manifest.exists():
        raise KanbanNotInitialized(
            "TaskPy data directory not found. Run `taskpy init` in this project."
        )
    return kanban, manifest


def ensure_initialized(root: Optional[Path] = None):
    _kanban_paths(root)


def load_manifest(root: Optional[Path] = None) -> List[Dict[str, str]]:
    """Read manifest.tsv and return a list of dictionaries."""
    _, manifest = _kanban_paths(root)
    with manifest.open("r", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [dict(row) for row in reader]


def _info_dir(root: Optional[Path] = None) -> Path:
    kanban, _ = _kanban_paths(root)
    info = kanban / "info"
    if not info.exists():
        raise KanbanNotInitialized(
            "TaskPy info directory missing. Run `taskpy init` in this project."
        )
    return info


def _load_toml(name: str, root: Optional[Path] = None) -> Dict[str, Any]:
    info = _info_dir(root)
    target = info / name
    if not target.exists():
        return {}
    with target.open("rb") as handle:
        return tomllib.load(handle)


def load_epics(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    data = _load_toml("epics.toml", root)
    epics: Dict[str, Dict[str, Any]] = {}
    for name, values in data.items():
        epics[name] = {
            "description": values.get("description", ""),
            "active": bool(values.get("active", True)),
            "story_point_budget": values.get("story_point_budget"),
        }
    return epics


def load_milestones(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    data = _load_toml("milestones.toml", root)
    return {name: values for name, values in data.items()}


def load_nfrs(root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    data = _load_toml("nfrs.toml", root)
    return {name: values for name, values in data.items()}


def make_task_id(epic: str, number: int) -> str:
    if number <= 99:
        return f"{epic}-{number:02d}"
    if number <= 999:
        return f"{epic}-{number:03d}"
    raise ValueError("Task number exceeds 999")


def parse_task_id(task_id: str) -> Tuple[str, int]:
    match = re.match(r"^([A-Z]+)-(\d+)$", task_id)
    if not match:
        raise ValueError(f"Invalid task ID format: {task_id}")
    epic, number = match.groups()
    return epic, int(number)


def next_task_number(epic: str, root: Optional[Path] = None) -> int:
    rows = load_manifest(root)
    numbers = [
        int(row.get("number", 0))
        for row in rows
        if row.get("epic", "").upper() == epic.upper()
    ]
    return (max(numbers) if numbers else 0) + 1


def next_auto_id(root: Optional[Path] = None) -> int:
    kanban, _ = _kanban_paths(root)
    sequence_file = kanban / SEQUENCE_FILENAME
    if not sequence_file.exists():
        last = 0
    else:
        content = sequence_file.read_text().strip()
        last = int(content) if content else 0
    next_id = last + 1
    sequence_file.write_text(f"{next_id}\n")
    return next_id


def get_task_path(task_id: str, status: str, root: Optional[Path] = None) -> Path:
    kanban, _ = _kanban_paths(root)
    return kanban / "status" / status / f"{task_id}.md"


def get_trash_dir(root: Optional[Path] = None) -> Path:
    """Return the trash directory path, creating it if needed."""
    kanban, _ = _kanban_paths(root)
    trash_dir = kanban / TRASH_DIRNAME
    trash_dir.mkdir(parents=True, exist_ok=True)
    return trash_dir


def find_trash_file(auto_id: int, root: Optional[Path] = None) -> Optional[Path]:
    """Find a trashed task file by auto_id."""
    trash_dir = get_trash_dir(root)
    for candidate in sorted(trash_dir.glob(f"{auto_id}.*.md")):
        if candidate.is_file():
            return candidate
    return None


def load_task_from_path(path: Path) -> TaskRecord:
    """Load a task directly from an explicit path."""
    if not path.exists():
        raise FileNotFoundError(f"Task file not found: {path}")
    return _read_task_file(path)


def get_manifest_row(task_id: str, root: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """Return a manifest row for a specific task ID."""
    rows = load_manifest(root)
    task_id = task_id.upper()
    for row in rows:
        if row.get("id", "").upper() == task_id:
            return row
    return None


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
    elif mode == "id":
        key_fn = lambda r: r.get("id", "")
    elif mode == "epic":
        key_fn = lambda r: r.get("epic", "")
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
    for key, value in list(metadata.items()):
        if key.startswith("references."):
            _, ref_key = key.split(".", 1)
            references.setdefault(ref_key, value)

    verification = metadata.get("verification") or {}
    if not isinstance(verification, dict):
        verification = {}
    for key, value in list(metadata.items()):
        if key.startswith("verification."):
            _, ver_key = key.split(".", 1)
            verification.setdefault(ver_key, value)

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


def append_issue(task_path: Path, description: str):
    """Append an issue entry to a task markdown file."""
    timestamp = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")
    issue_line = f"- **{timestamp}** - {description}".strip() + "\n"

    content = task_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    issues_idx = None
    in_code_block = False

    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if (
            line.strip() == "## ISSUES"
            and not in_code_block
            and not line.startswith((" ", "\t", "-", "*"))
        ):
            issues_idx = idx
            break

    if issues_idx is not None:
        next_section = len(lines)
        for idx in range(issues_idx + 1, len(lines)):
            if lines[idx].startswith("## ") and lines[idx].strip() != "## ISSUES":
                next_section = idx
                break
        lines.insert(next_section, issue_line)
        content = "\n".join(lines)
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += f"\n## ISSUES\n\n{issue_line}"

    task_path.write_text(content, encoding="utf-8")


def read_issues(task_path: Path) -> List[str]:
    """Read the ISSUES section from a task file."""
    content = task_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    issues_idx = None
    in_code_block = False

    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
        if line.strip() == "## ISSUES" and not in_code_block:
            issues_idx = idx
            break

    if issues_idx is None:
        return []

    issues: List[str] = []
    for idx in range(issues_idx + 1, len(lines)):
        line = lines[idx]
        if line.startswith("## ") and line.strip() != "## ISSUES":
            break
        if line.strip().startswith("- "):
            issues.append(line.strip())

    return issues


def _serialize_task(task: TaskRecord) -> str:
    data = task.to_frontmatter_dict()
    lines = ["---"]

    def add_simple(key: str, value: Any):
        if value is None:
            return
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        else:
            lines.append(f"{key}: {value}")

    for key in [
        "id",
        "title",
        "epic",
        "number",
        "status",
        "story_points",
        "priority",
        "created",
        "updated",
        "assigned",
        "milestone",
        "blocked_reason",
        "in_sprint",
        "commit_hash",
        "demotion_reason",
        "resolution",
        "resolution_reason",
        "duplicate_of",
        "auto_id",
    ]:
        value = data.get(key)
        add_simple(key, value)

    for key in ["tags", "dependencies", "blocks", "nfrs"]:
        values = data.get(key) or []
        if values:
            lines.append(f"{key}: [{', '.join(values)}]")

    references = data.get("references") or {}
    for ref_type in ["code", "docs", "plans", "tests"]:
        entries = references.get(ref_type) or []
        if entries:
            lines.append(f"references.{ref_type}: [{', '.join(entries)}]")

    verification = data.get("verification") or {}
    if verification.get("command"):
        lines.append(f"verification.command: {verification['command']}")
    if verification.get("status"):
        lines.append(f"verification.status: {verification['status']}")

    history = data.get("history") or []
    if history:
        lines.append("history:")
        for entry in history:
            entry_yaml = yaml.dump(entry, default_flow_style=False, sort_keys=False)
            entry_lines = entry_yaml.strip().split("\n")
            if entry_lines:
                lines.append(f"  - {entry_lines[0]}")
                for line in entry_lines[1:]:
                    if line.strip():
                        lines.append(f"    {line}")

    lines.append("---")
    lines.append("")
    lines.append(task.content.rstrip() + "\n")
    return "\n".join(lines)


def _update_manifest_row(task: TaskRecord, root: Optional[Path] = None):
    _, manifest = _kanban_paths(root)
    rows: List[List[str]] = []
    header = [
        "id",
        "epic",
        "number",
        "status",
        "title",
        "story_points",
        "priority",
        "created",
        "updated",
        "tags",
        "dependencies",
        "blocks",
        "verification_status",
        "assigned",
        "milestone",
        "blocked_reason",
        "in_sprint",
        "commit_hash",
        "demotion_reason",
        "auto_id",
    ]
    if manifest.exists():
        with manifest.open("r", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            try:
                header = next(reader)
            except StopIteration:
                header = header
            for row in reader:
                if row and row[0] != task.id:
                    rows.append(row)
    rows.append(task.to_manifest_row())
    with manifest.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)


def remove_manifest_entry(task_id: str, root: Optional[Path] = None):
    _, manifest = _kanban_paths(root)
    if not manifest.exists():
        return
    rows = []
    with manifest.open("r", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            return
        rows.append(header)
        for row in reader:
            if not row or row[0] == task_id:
                continue
            rows.append(row)
    with manifest.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerows(rows)


def write_task(task: TaskRecord, root: Optional[Path] = None, update_manifest: bool = True) -> Path:
    task.updated = utc_now()
    kanban, _ = _kanban_paths(root)
    status_dir = kanban / "status" / task.status
    status_dir.mkdir(parents=True, exist_ok=True)
    path = status_dir / f"{task.id}.md"
    path.write_text(_serialize_task(task))
    if update_manifest:
        _update_manifest_row(task, root)
    return path


def open_in_editor(path: Path):
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    try:
        subprocess.run([editor, str(path)], check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - user env
        raise RuntimeError(f"Editor exited with error: {exc}") from exc
