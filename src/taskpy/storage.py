"""
Storage and persistence layer for TaskPy.

Handles:
- Task file I/O (markdown with YAML frontmatter)
- Manifest management (TSV index)
- Epic and NFR configuration
- Kanban directory structure
"""

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import sys

# TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from taskpy.models import (
    Task, Epic, NFR, Milestone, TaskStatus, Priority,
    TaskReference, Verification, VerificationStatus, utc_now
)


class StorageError(Exception):
    """Base exception for storage errors."""
    pass


def detect_project_type(root_path: Path) -> tuple[Optional[str], bool]:
    """
    Detect project type based on marker files.

    Returns:
        (project_type, auto_detected) where project_type is one of:
        "rust", "python", "node", "generic" or None if detection fails
        auto_detected is True if type was detected, False otherwise
    """
    # Detection priority order
    if (root_path / "Cargo.toml").exists():
        return ("rust", True)

    if (root_path / "pyproject.toml").exists() or \
       (root_path / "setup.py").exists() or \
       (root_path / "requirements.txt").exists():
        return ("python", True)

    if (root_path / "package.json").exists():
        return ("node", True)

    # Check for shell project (multiple .sh files in bin/ or src/)
    bin_dir = root_path / "bin"
    src_dir = root_path / "src"
    shell_count = 0
    if bin_dir.exists():
        shell_count += len(list(bin_dir.glob("*.sh")))
    if src_dir.exists():
        shell_count += len(list(src_dir.glob("*.sh")))

    if shell_count >= 2:
        return ("shell", True)

    # Default to generic
    return ("generic", False)


def get_project_defaults(project_type: str) -> dict:
    """
    Get default configuration for a project type.

    Returns:
        Dict with verify_command, code_patterns, test_patterns
    """
    defaults = {
        "rust": {
            "verify_command": "cargo test",
            "code_patterns": ["src/**/*.rs", "tests/**/*.rs"],
            "test_patterns": ["tests/**/*.rs"],
        },
        "python": {
            "verify_command": "pytest tests/",
            "code_patterns": ["src/**/*.py", "tests/**/*.py"],
            "test_patterns": ["tests/**/*.py", "test_*.py"],
        },
        "node": {
            "verify_command": "npm test",
            "code_patterns": ["src/**/*.js", "src/**/*.ts", "test/**/*.js"],
            "test_patterns": ["test/**/*.js", "__tests__/**/*.js"],
        },
        "shell": {
            "verify_command": "./run_tests.sh",
            "code_patterns": ["bin/**/*.sh", "src/**/*.sh"],
            "test_patterns": ["tests/**/*.sh", "test_*.sh"],
        },
        "generic": {
            "verify_command": "",
            "code_patterns": ["src/**/*"],
            "test_patterns": ["tests/**/*", "test/**/*"],
        },
    }

    return defaults.get(project_type, defaults["generic"])


class TaskStorage:
    """
    Manages task persistence and retrieval.

    Directory structure:
        data/kanban/
        ├── info/
        │   ├── epics.toml
        │   ├── nfrs.toml
        │   └── config.toml
        ├── status/
        │   ├── backlog/
        │   ├── ready/
        │   ├── in_progress/
        │   ├── review/
        │   ├── done/
        │   └── archived/
        ├── manifest.tsv
        └── references/
            └── PLAN-*.md
    """

    def __init__(self, root_path: Path):
        """
        Initialize storage at given root path.

        Args:
            root_path: Project root directory
        """
        self.root = root_path
        self.kanban = root_path / "data" / "kanban"
        self.info_dir = self.kanban / "info"
        self.status_dir = self.kanban / "status"
        self.refs_dir = self.kanban / "references"
        self.manifest_file = self.kanban / "manifest.tsv"

    def is_initialized(self) -> bool:
        """Check if kanban structure exists."""
        return (
            self.kanban.exists()
            and self.info_dir.exists()
            and self.status_dir.exists()
            and self.manifest_file.exists()
        )

    def initialize(self, force: bool = False, project_type: Optional[str] = None):
        """
        Create kanban directory structure.

        Args:
            force: If True, recreate structure even if it exists
            project_type: Explicit project type ("rust", "python", "node", "shell", "generic")
                         If None, auto-detect from project files

        Raises:
            StorageError: If already initialized and force=False

        Returns:
            Tuple of (project_type, auto_detected) where auto_detected indicates
            whether the type was auto-detected or explicitly set
        """
        if self.is_initialized() and not force:
            raise StorageError("TaskPy already initialized. Use --force to reinitialize.")

        # Detect or validate project type
        if project_type is None:
            detected_type, auto_detected = detect_project_type(self.root)
            project_type = detected_type
        else:
            # Explicit type provided
            auto_detected = False
            # Validate project type
            valid_types = ["rust", "python", "node", "shell", "generic"]
            if project_type not in valid_types:
                raise StorageError(
                    f"Invalid project type: {project_type}. "
                    f"Valid types: {', '.join(valid_types)}"
                )

        # Create directory structure
        self.kanban.mkdir(parents=True, exist_ok=True)
        self.info_dir.mkdir(exist_ok=True)
        self.status_dir.mkdir(exist_ok=True)
        self.refs_dir.mkdir(exist_ok=True)

        # Create status subdirectories
        for status in TaskStatus:
            (self.status_dir / status.value).mkdir(exist_ok=True)

        # Create default epics config
        if not (self.info_dir / "epics.toml").exists() or force:
            self._create_default_epics()

        # Create default NFRs config
        if not (self.info_dir / "nfrs.toml").exists() or force:
            self._create_default_nfrs()

        # Create default milestones config
        if not (self.info_dir / "milestones.toml").exists() or force:
            self._create_default_milestones()

        # Create default config with project type
        if not (self.info_dir / "config.toml").exists() or force:
            self._create_default_config(project_type, auto_detected)

        # Create manifest header
        if not self.manifest_file.exists() or force:
            self._create_manifest_header()

        # Update .gitignore
        self._update_gitignore()

        return (project_type, auto_detected)

    def _create_default_epics(self):
        """Create default epics.toml with standard epic types."""
        content = """# Epic definitions for TaskPy
# Define your epic types here. Each epic gets its own namespace (EPIC-NNN).

[BUGS]
description = "Bug fixes and corrections"
active = true

[DOCS]
description = "Documentation work"
active = true

[FEAT]
description = "New features and enhancements"
active = true

[REF]
description = "Refactoring and code cleanup"
active = true

[RX]
description = "Research and exploration"
prefix = "RX"
active = true

[UAT]
description = "User acceptance testing"
active = true

[QOL]
description = "Quality of life improvements"
active = true

[TEST]
description = "Test infrastructure and improvements"
active = true

[DEPS]
description = "Dependency management and updates"
active = true

[INFRA]
description = "Infrastructure and tooling"
active = true

[M0]
description = "Milestone 0: Setup/skeleton/foundation"
active = true

# Add custom epics as needed
# [MYEPIC]
# description = "Custom epic description"
# prefix = "CUSTOM"  # Optional: use different prefix than epic name
# active = true
# story_point_budget = 100  # Optional: SP limit for this epic
"""
        (self.info_dir / "epics.toml").write_text(content)

    def _create_default_nfrs(self):
        """Create default nfrs.toml with standard NFRs."""
        content = """# Non-Functional Requirements (NFRs)
# Define NFRs that can be linked to tasks for compliance tracking.

[NFR-SEC-001]
category = "SEC"
number = 1
title = "Code must be free of common security vulnerabilities"
description = "No SQL injection, XSS, command injection, path traversal, etc."
verification = "Run security linters and manual code review"
default = true

[NFR-TEST-001]
category = "TEST"
number = 1
title = "All code must have passing tests"
description = "Unit tests, integration tests as appropriate. No fake/placeholder tests."
verification = "cargo test --all or testpy run"
default = true

[NFR-DOC-001]
category = "DOC"
number = 1
title = "Public APIs must be documented"
description = "All public functions, types, and modules must have documentation comments."
verification = "cargo doc --no-deps or featpy lint"
default = true

[NFR-PERF-001]
category = "PERF"
number = 1
title = "Operations must complete in reasonable time"
description = "No operations that hang indefinitely or cause unacceptable latency."
verification = "Performance testing and profiling"
default = false

[NFR-SCALE-001]
category = "SCALE"
number = 1
title = "Must handle expected data volumes"
description = "System must scale to handle expected user/data load."
verification = "Load testing and benchmarking"
default = false

# Add custom NFRs as needed
# [NFR-CUSTOM-001]
# category = "CUSTOM"
# number = 1
# title = "Your NFR title"
# description = "Detailed description"
# verification = "How to verify compliance"
# default = false
"""
        (self.info_dir / "nfrs.toml").write_text(content)

    def _create_default_milestones(self):
        """Create default milestones.toml with example milestones."""
        content = """# Milestone definitions for TaskPy
# Define project milestones/phases here. Milestones organize multi-phase work.
# IDs use semantic versioning (milestone-1, milestone-1.5, milestone-2).
# Priority field controls execution order (1=first, 2=second, etc.).

[milestone-1]
name = "Foundation MVP"
description = "Core functionality and basic workflow"
priority = 1
status = "active"
goal_sp = 50

[milestone-2]
name = "Feature Complete"
description = "All planned features implemented"
priority = 2
status = "planned"
goal_sp = 100

[milestone-3]
name = "Polish and Release"
description = "UX improvements, documentation, and release prep"
priority = 3
status = "planned"
goal_sp = 40

# Add custom milestones as needed
# [milestone-1.5]
# name = "Security Hardening"
# description = "Address security audit findings"
# priority = 2  # Injected between milestone-1 and milestone-2
# status = "planned"
# goal_sp = 20
"""
        (self.info_dir / "milestones.toml").write_text(content)

    def _create_default_config(self, project_type: str = "generic", auto_detected: bool = False):
        """Create default config.toml with project-specific defaults."""
        # Get project defaults
        defaults = get_project_defaults(project_type)

        # Build verify command comment
        verify_cmd = defaults["verify_command"]
        verify_comment = f'test_command = "{verify_cmd}"' if verify_cmd else '# test_command = "pytest tests/"'

        content = f"""# TaskPy configuration

[project]
# Project type: rust, python, node, shell, generic
type = "{project_type}"

# Whether project type was auto-detected
auto_detected = {str(auto_detected).lower()}

[project.defaults]
# Default verification command for this project type
verify_command = "{verify_cmd}"

# Code file patterns
code_patterns = {defaults["code_patterns"]}

# Test file patterns
test_patterns = {defaults["test_patterns"]}

[general]
# Default story point estimate for new tasks
default_story_points = 0

# Auto-apply default NFRs to all new tasks
apply_default_nfrs = true

# Default priority for new tasks
default_priority = "medium"

[workflow]
# Available task statuses (in workflow order)
statuses = ["backlog", "ready", "in_progress", "review", "done", "archived"]

# Auto-archive done tasks after N days (0 = never)
auto_archive_days = 0

[verification]
# Test runner command (uses project.defaults.verify_command if not set)
{verify_comment}

# Require tests to pass before promoting to 'done'
require_tests = false

[display]
# Default output mode: "pretty" or "data"
default_view = "pretty"

# Show story points in task lists
show_story_points = true

# Show tags in task lists
show_tags = true
"""
        (self.info_dir / "config.toml").write_text(content)

    def _create_manifest_header(self):
        """Create manifest TSV with header row."""
        headers = [
            "id", "epic", "number", "status", "title",
            "story_points", "priority", "created", "updated",
            "tags", "dependencies", "blocks", "verification_status", "assigned",
            "milestone", "blocked_reason", "in_sprint", "commit_hash", "demotion_reason"
        ]
        with open(self.manifest_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(headers)

    def _update_gitignore(self):
        """Add data/kanban to .gitignore if not already present."""
        gitignore_path = self.root / ".gitignore"

        # Read existing .gitignore or create new
        if gitignore_path.exists():
            content = gitignore_path.read_text()
            lines = content.splitlines()
        else:
            lines = []

        # Check if data/kanban is already ignored
        kanban_patterns = [
            "data/kanban/",
            "/data/kanban/",
            "data/kanban",
            "/data/kanban",
        ]

        has_kanban = any(
            any(pattern in line for pattern in kanban_patterns)
            for line in lines
        )

        if not has_kanban:
            # Add kanban directory to gitignore
            if lines and lines[-1].strip():
                lines.append("")  # Blank line before new section
            lines.append("# TaskPy kanban data")
            lines.append("data/kanban/")
            lines.append("")

            gitignore_path.write_text("\n".join(lines) + "\n")

    def load_epics(self) -> Dict[str, Epic]:
        """Load epic definitions from epics.toml."""
        if tomllib is None:
            raise StorageError("TOML library not available. Install tomli for Python <3.11")

        epics_file = self.info_dir / "epics.toml"
        if not epics_file.exists():
            return {}

        with open(epics_file, 'rb') as f:
            data = tomllib.load(f)

        epics = {}
        for name, config in data.items():
            epics[name] = Epic(
                name=name,
                description=config.get('description', ''),
                prefix=config.get('prefix'),
                active=config.get('active', True),
                story_point_budget=config.get('story_point_budget'),
            )

        return epics

    def load_nfrs(self) -> Dict[str, NFR]:
        """Load NFR definitions from nfrs.toml."""
        if tomllib is None:
            raise StorageError("TOML library not available. Install tomli for Python <3.11")

        nfrs_file = self.info_dir / "nfrs.toml"
        if not nfrs_file.exists():
            return {}

        with open(nfrs_file, 'rb') as f:
            data = tomllib.load(f)

        nfrs = {}
        for nfr_id, config in data.items():
            nfrs[nfr_id] = NFR(
                id=nfr_id,
                category=config['category'],
                number=config['number'],
                title=config['title'],
                description=config['description'],
                verification=config.get('verification'),
                default=config.get('default', False),
            )

        return nfrs

    def load_milestones(self) -> Dict[str, Milestone]:
        """Load milestone definitions from milestones.toml."""
        if tomllib is None:
            raise StorageError("TOML library not available. Install tomli for Python <3.11")

        milestones_file = self.info_dir / "milestones.toml"
        if not milestones_file.exists():
            return {}

        with open(milestones_file, 'rb') as f:
            data = tomllib.load(f)

        milestones = {}
        for milestone_id, config in data.items():
            milestones[milestone_id] = Milestone(
                id=milestone_id,
                name=config['name'],
                description=config['description'],
                priority=config['priority'],
                status=config.get('status', 'planned'),
                goal_sp=config.get('goal_sp'),
                blocked_reason=config.get('blocked_reason'),
            )

        return milestones

    def get_next_task_number(self, epic: str) -> int:
        """
        Get next available task number for an epic.

        Args:
            epic: Epic name (e.g., "BUGS")

        Returns:
            Next sequential number
        """
        # Read manifest and find highest number for this epic
        if not self.manifest_file.exists():
            return 1

        max_num = 0
        with open(self.manifest_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if row['epic'] == epic:
                    num = int(row['number'])
                    max_num = max(max_num, num)

        return max_num + 1

    def get_task_path(self, task_id: str, status: TaskStatus) -> Path:
        """Get filesystem path for a task file."""
        return self.status_dir / status.value / f"{task_id}.md"

    def find_task_file(self, task_id: str) -> Optional[Tuple[Path, TaskStatus]]:
        """
        Find a task file across all status directories.

        Args:
            task_id: Task ID (e.g., "BUGS-001")

        Returns:
            Tuple of (path, status) if found, None otherwise
        """
        for status in TaskStatus:
            path = self.get_task_path(task_id, status)
            if path.exists():
                return path, status
        return None

    def read_task_file(self, path: Path) -> Task:
        """
        Read a task from a markdown file with YAML frontmatter.

        Format:
            ---
            id: BUGS-001
            title: Fix thing
            ...
            ---
            # Task content here

        Args:
            path: Path to task markdown file

        Returns:
            Task object

        Raises:
            StorageError: If file format is invalid
        """
        content = path.read_text()

        # Parse frontmatter
        if not content.startswith('---\n'):
            raise StorageError(f"Invalid task file format: {path} (missing frontmatter)")

        # Find end of frontmatter
        end_idx = content.find('\n---\n', 4)
        if end_idx == -1:
            raise StorageError(f"Invalid task file format: {path} (unclosed frontmatter)")

        frontmatter_text = content[4:end_idx]
        body = content[end_idx + 5:].strip()

        # Parse YAML frontmatter (simplified - just handle key: value)
        metadata = self._parse_simple_yaml(frontmatter_text)

        # Build Task object
        task = Task(
            id=metadata['id'],
            title=metadata['title'],
            epic=metadata['epic'],
            number=int(metadata['number']),
            status=TaskStatus(metadata.get('status', 'backlog')),
            story_points=int(metadata.get('story_points', 0)),
            priority=Priority(metadata.get('priority', 'medium')),
            created=datetime.fromisoformat(metadata['created']),
            updated=datetime.fromisoformat(metadata['updated']),
            assigned=metadata.get('assigned'),
            milestone=metadata.get('milestone'),
            blocked_reason=metadata.get('blocked_reason'),
            in_sprint=metadata.get('in_sprint', 'false').lower() == 'true',
            commit_hash=metadata.get('commit_hash'),
            demotion_reason=metadata.get('demotion_reason'),
            tags=self._parse_list(metadata.get('tags', '')),
            dependencies=self._parse_list(metadata.get('dependencies', '')),
            blocks=self._parse_list(metadata.get('blocks', '')),
            nfrs=self._parse_list(metadata.get('nfrs', '')),
            content=body,
        )

        # Parse references (if present)
        if 'references.code' in metadata:
            task.references.code = self._parse_list(metadata.get('references.code', ''))
        if 'references.docs' in metadata:
            task.references.docs = self._parse_list(metadata.get('references.docs', ''))
        if 'references.plans' in metadata:
            task.references.plans = self._parse_list(metadata.get('references.plans', ''))
        if 'references.tests' in metadata:
            task.references.tests = self._parse_list(metadata.get('references.tests', ''))

        # Parse verification (if present)
        if 'verification.command' in metadata:
            task.verification.command = metadata.get('verification.command')
        if 'verification.status' in metadata:
            task.verification.status = VerificationStatus(metadata.get('verification.status'))

        return task

    def write_task_file(self, task: Task):
        """
        Write task to markdown file with YAML frontmatter.

        Args:
            task: Task to write
        """
        # Update timestamp
        task.updated = utc_now()

        # Get file path
        path = self.get_task_path(task.id, task.status)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Build frontmatter
        fm = task.to_frontmatter_dict()
        frontmatter_lines = ["---"]

        # Simple fields
        for key in ['id', 'title', 'epic', 'number', 'status', 'story_points',
                    'priority', 'created', 'updated', 'assigned', 'milestone', 'blocked_reason',
                    'in_sprint', 'commit_hash', 'demotion_reason']:
            value = fm[key]
            if value is not None:
                frontmatter_lines.append(f"{key}: {value}")

        # List fields
        for key in ['tags', 'dependencies', 'blocks', 'nfrs']:
            values = fm[key]
            if values:
                frontmatter_lines.append(f"{key}: [{', '.join(values)}]")

        # References (nested)
        refs = fm['references']
        for ref_type in ['code', 'docs', 'plans', 'tests']:
            if refs[ref_type]:
                frontmatter_lines.append(f"references.{ref_type}: [{', '.join(refs[ref_type])}]")

        # Verification (nested)
        verif = fm['verification']
        if verif['command']:
            frontmatter_lines.append(f"verification.command: {verif['command']}")
        frontmatter_lines.append(f"verification.status: {verif['status']}")

        frontmatter_lines.append("---")

        # Combine frontmatter and body
        full_content = "\n".join(frontmatter_lines) + "\n\n" + task.content

        # Write file
        path.write_text(full_content)

        # Update manifest
        self._update_manifest_row(task)

    def _update_manifest_row(self, task: Task):
        """Update or insert task in manifest TSV."""
        # Read existing rows
        rows = []
        task_found = False

        if self.manifest_file.exists():
            with open(self.manifest_file, 'r', newline='') as f:
                reader = csv.reader(f, delimiter='\t')
                headers = next(reader)
                for row in reader:
                    if row and row[0] == task.id:
                        # Update existing row
                        rows.append(task.to_manifest_row())
                        task_found = True
                    else:
                        rows.append(row)

        # Append if new task
        if not task_found:
            rows.append(task.to_manifest_row())

        # Write back
        with open(self.manifest_file, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(headers)
            writer.writerows(rows)

    def _parse_simple_yaml(self, text: str) -> Dict[str, str]:
        """Parse simplified YAML (key: value format)."""
        data = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
        return data

    def _parse_list(self, value: str) -> List[str]:
        """Parse list from YAML value like '[a, b, c]' or 'a,b,c'."""
        if not value:
            return []
        value = value.strip()
        if value.startswith('[') and value.endswith(']'):
            value = value[1:-1]
        return [item.strip() for item in value.split(',') if item.strip()]
