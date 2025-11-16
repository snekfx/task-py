"""
Core data models for TaskPy.

Defines Task, Epic, NFR, and Session models with validation.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import re


class TaskStatus(Enum):
    """Task lifecycle states (Kanban)."""
    STUB = "stub"
    BACKLOG = "backlog"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    QA = "qa"
    DONE = "done"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class Priority(Enum):
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(Enum):
    """Test verification status."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskReference:
    """References to code, docs, or other resources."""
    code: List[str] = field(default_factory=list)  # src/file.rs:10-20
    docs: List[str] = field(default_factory=list)  # docs/design.md
    plans: List[str] = field(default_factory=list)  # PLAN-01
    tests: List[str] = field(default_factory=list)  # tests/integration/foo.rs

    def to_dict(self) -> Dict[str, List[str]]:
        return asdict(self)


@dataclass
class Verification:
    """Test verification configuration."""
    command: Optional[str] = None  # "cargo test feature::test"
    status: VerificationStatus = VerificationStatus.PENDING
    last_run: Optional[datetime] = None
    output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            'command': self.command,
            'status': self.status.value,
        }
        if self.last_run:
            data['last_run'] = self.last_run.isoformat()
        if self.output:
            data['output'] = self.output
        return data


@dataclass
class Task:
    """
    Structured task with metadata and markdown content.

    Tasks are stored as markdown files with YAML frontmatter.
    """
    # Required fields
    id: str  # EPIC-NNN (e.g., BUGS-001)
    title: str
    epic: str  # Epic category (e.g., BUGS)
    number: int  # Sequential number within epic

    # Metadata
    status: TaskStatus = TaskStatus.BACKLOG
    story_points: int = 0
    priority: Priority = Priority.MEDIUM
    created: datetime = field(default_factory=datetime.utcnow)
    updated: datetime = field(default_factory=datetime.utcnow)

    # Organization
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Task IDs this depends on
    blocks: List[str] = field(default_factory=list)  # Task IDs this blocks
    milestone: Optional[str] = None  # Milestone ID (e.g., "milestone-1")
    blocked_reason: Optional[str] = None  # Reason if status is BLOCKED

    # Compliance
    nfrs: List[str] = field(default_factory=list)  # NFR-XXX-NNN references

    # References
    references: TaskReference = field(default_factory=TaskReference)

    # Verification
    verification: Verification = field(default_factory=Verification)

    # Content (markdown body)
    content: str = ""

    # Session tracking
    assigned: Optional[str] = None  # Session ID or agent name
    in_sprint: bool = False  # Whether task is in active sprint

    # Completion tracking
    commit_hash: Optional[str] = None  # Git commit hash when task completed
    demotion_reason: Optional[str] = None  # Reason for demotion from done

    @property
    def filename(self) -> str:
        """Generate filename for this task."""
        return f"{self.id}.md"

    @property
    def epic_prefix(self) -> str:
        """Extract epic prefix (e.g., 'BUGS' from 'BUGS-001')."""
        return self.id.split('-')[0]

    @classmethod
    def parse_task_id(cls, task_id: str) -> tuple[str, int]:
        """
        Parse task ID into epic and number.

        Args:
            task_id: Task ID like "BUGS-001" or "DOCS-42"

        Returns:
            Tuple of (epic, number)

        Raises:
            ValueError: If ID format is invalid
        """
        match = re.match(r'^([A-Z]+)-(\d+)$', task_id)
        if not match:
            raise ValueError(f"Invalid task ID format: {task_id} (expected EPIC-NNN)")
        epic, number = match.groups()
        return epic, int(number)

    @classmethod
    def make_task_id(cls, epic: str, number: int) -> str:
        """
        Generate task ID from epic and number.
        Uses 2-digit format for 1-99, 3-digit format for 100-999.
        """
        if number <= 99:
            return f"{epic}-{number:02d}"
        elif number <= 999:
            return f"{epic}-{number:03d}"
        else:
            raise ValueError(f"Task number {number} exceeds maximum of 999")

    def to_frontmatter_dict(self) -> Dict[str, Any]:
        """Convert task metadata to YAML frontmatter dict."""
        return {
            'id': self.id,
            'title': self.title,
            'epic': self.epic,
            'number': self.number,
            'status': self.status.value,
            'story_points': self.story_points,
            'priority': self.priority.value,
            'created': self.created.isoformat(),
            'updated': self.updated.isoformat(),
            'assigned': self.assigned,
            'milestone': self.milestone,
            'blocked_reason': self.blocked_reason,
            'in_sprint': self.in_sprint,
            'commit_hash': self.commit_hash,
            'demotion_reason': self.demotion_reason,
            'tags': self.tags,
            'dependencies': self.dependencies,
            'blocks': self.blocks,
            'nfrs': self.nfrs,
            'references': self.references.to_dict(),
            'verification': self.verification.to_dict(),
        }

    def to_manifest_row(self) -> List[str]:
        """Convert to TSV manifest row."""
        return [
            self.id,
            self.epic,
            str(self.number),
            self.status.value,
            self.title,
            str(self.story_points),
            self.priority.value,
            self.created.isoformat(),
            self.updated.isoformat(),
            ','.join(self.tags),
            ','.join(self.dependencies),
            ','.join(self.blocks),
            self.verification.status.value,
            self.assigned or '',
            self.milestone or '',
            self.blocked_reason or '',
            str(self.in_sprint).lower(),
            self.commit_hash or '',
            self.demotion_reason or '',
        ]


@dataclass
class Epic:
    """
    Epic definition (task category).

    Examples: BUGS, DOCS, REF (refactor), RX (research), FEAT, etc.
    """
    name: str  # BUGS, DOCS, REF, etc.
    description: str
    prefix: Optional[str] = None  # Optional custom prefix
    active: bool = True
    story_point_budget: Optional[int] = None  # Optional SP limit

    @property
    def task_prefix(self) -> str:
        """Get the prefix used for task IDs."""
        return self.prefix or self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            'description': self.description,
            'prefix': self.prefix,
            'active': self.active,
            'story_point_budget': self.story_point_budget,
        }


@dataclass
class NFR:
    """
    Non-Functional Requirement definition.

    NFRs can be linked to tasks for compliance tracking.
    """
    id: str  # NFR-SEC-001, NFR-PERF-002, etc.
    category: str  # SEC, PERF, SCALE, etc.
    number: int
    title: str
    description: str
    verification: Optional[str] = None  # How to verify compliance
    default: bool = False  # Is this a default NFR for all tasks?

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'description': self.description,
            'verification': self.verification,
            'default': self.default,
        }


@dataclass
class Milestone:
    """
    Milestone definition for organizing multi-phase work.

    Milestones use semantic IDs (milestone-1, milestone-1.5) with
    independent priority ordering for execution.
    """
    id: str  # milestone-1, milestone-1.5, milestone-2, etc.
    name: str  # Human-readable milestone name
    description: str
    priority: int  # Execution order (1=first, 2=second, etc.)
    status: str = "planned"  # planned, active, blocked, completed
    goal_sp: Optional[int] = None  # Target story points
    blocked_reason: Optional[str] = None  # Reason if status is blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'goal_sp': self.goal_sp,
            'blocked_reason': self.blocked_reason,
        }


@dataclass
class Session:
    """
    Development session tracking.

    Sessions are logged to sessions.jsonl for HANDOFF automation.
    """
    session_id: str
    started: datetime
    ended: Optional[datetime] = None
    focus: Optional[str] = None  # What was worked on
    tasks_completed: List[str] = field(default_factory=list)
    tasks_started: List[str] = field(default_factory=list)
    tasks_blocked: List[str] = field(default_factory=list)
    story_points_completed: int = 0
    files_modified: List[str] = field(default_factory=list)
    commits: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = {
            'session_id': self.session_id,
            'started': self.started.isoformat(),
            'focus': self.focus,
            'tasks_completed': self.tasks_completed,
            'tasks_started': self.tasks_started,
            'tasks_blocked': self.tasks_blocked,
            'story_points_completed': self.story_points_completed,
            'files_modified': self.files_modified,
            'commits': self.commits,
            'notes': self.notes,
        }
        if self.ended:
            data['ended'] = self.ended.isoformat()
        return data
