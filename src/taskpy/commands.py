"""
Command implementations for TaskPy.

Each command is implemented as cmd_<name>(args) function.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from taskpy.models import Task, TaskStatus, Priority, TaskReference, Verification
from taskpy.storage import TaskStorage, StorageError
from taskpy.output import (
    print_success, print_error, print_info, print_warning,
    display_task_card, display_kanban_column, rolo_table,
    get_output_mode, OutputMode
)


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def cmd_init(args):
    """Initialize TaskPy kanban structure."""
    storage = get_storage()

    try:
        storage.initialize(force=args.force)
        print_success(
            f"TaskPy initialized at: {storage.kanban}\n\n"
            f"Structure created:\n"
            f"  • data/kanban/info/     - Configuration (epics, NFRs)\n"
            f"  • data/kanban/status/   - Task files by status\n"
            f"  • data/kanban/manifest.tsv - Fast query index\n"
            f"  • .gitignore            - Updated to exclude kanban data\n\n"
            f"Next steps:\n"
            f"  1. Review epics: data/kanban/info/epics.toml\n"
            f"  2. Review NFRs: data/kanban/info/nfrs.toml\n"
            f"  3. Create your first task: taskpy create FEAT \"Your feature\"\n",
            "TaskPy Initialized"
        )
    except StorageError as e:
        print_error(str(e))
        sys.exit(1)


def cmd_create(args):
    """Create a new task."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Load epics to validate
    epics = storage.load_epics()
    epic_name = args.epic.upper()

    if epic_name not in epics:
        print_error(
            f"Unknown epic: {epic_name}\n"
            f"Available epics: {', '.join(epics.keys())}\n"
            f"Add new epic in: data/kanban/info/epics.toml"
        )
        sys.exit(1)

    if not epics[epic_name].active:
        print_warning(f"Epic {epic_name} is marked inactive")

    # Generate task ID
    number = storage.get_next_task_number(epic_name)
    task_id = Task.make_task_id(epic_name, number)

    # Parse title
    title = " ".join(args.title)

    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',')]

    # Create task
    task = Task(
        id=task_id,
        title=title,
        epic=epic_name,
        number=number,
        status=TaskStatus(args.status),
        story_points=args.story_points,
        priority=Priority(args.priority),
        tags=tags,
        content=f"# {title}\n\n## Description\n\n<!-- Add task description here -->\n\n## Acceptance Criteria\n\n- [ ] Criterion 1\n- [ ] Criterion 2\n\n## Notes\n\n<!-- Add notes here -->\n"
    )

    # Apply default NFRs
    nfrs = storage.load_nfrs()
    default_nfrs = [nfr_id for nfr_id, nfr in nfrs.items() if nfr.default]
    task.nfrs = default_nfrs

    # Save task
    try:
        storage.write_task_file(task)
        print_success(
            f"Created task: {task_id}\n"
            f"Title: {title}\n"
            f"Epic: {epic_name}\n"
            f"Status: {args.status}\n"
            f"Story Points: {args.story_points}\n"
            f"Priority: {args.priority}\n"
            f"Default NFRs: {len(default_nfrs)}\n\n"
            f"View: taskpy show {task_id}\n"
            f"Edit: taskpy edit {task_id}",
            f"Task {task_id} Created"
        )

        # Open in editor if requested
        if args.edit:
            _open_in_editor(storage.get_task_path(task_id, task.status))

    except Exception as e:
        print_error(f"Failed to create task: {e}")
        sys.exit(1)


def cmd_list(args):
    """List tasks with optional filters."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and apply filters
    tasks = _read_manifest_with_filters(storage, args)

    if not tasks:
        print_info("No tasks found matching filters")
        return

    # Display based on format
    if args.format == "ids":
        for task in tasks:
            print(task['id'])

    elif args.format == "tsv":
        # TSV output for scripting
        print("\t".join(["id", "epic", "status", "title", "sp", "priority"]))
        for task in tasks:
            print(f"{task['id']}\t{task['epic']}\t{task['status']}\t{task['title']}\t{task['story_points']}\t{task['priority']}")

    elif args.format == "cards":
        # Display each as a card
        for task in tasks:
            display_task_card(task)
            print()  # Spacing

    else:  # table
        headers = ["ID", "Title", "Status", "SP", "Priority"]
        rows = [
            [
                task['id'],
                task['title'][:50],  # Truncate long titles
                task['status'],
                task['story_points'],
                task['priority']
            ]
            for task in tasks
        ]
        rolo_table(headers, rows, f"Tasks ({len(tasks)} found)")


def cmd_show(args):
    """Display a task."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result

    try:
        task = storage.read_task_file(path)

        # Display as card
        task_dict = {
            'id': task.id,
            'title': task.title,
            'status': task.status.value,
            'priority': task.priority.value,
            'story_points': task.story_points,
            'tags': task.tags,
            'dependencies': task.dependencies,
            'assigned': task.assigned,
            'content': task.content,
        }
        display_task_card(task_dict)

        # Show metadata if in data mode
        if get_output_mode() == OutputMode.DATA:
            print(f"\nCreated: {task.created.isoformat()}")
            print(f"Updated: {task.updated.isoformat()}")
            if task.nfrs:
                print(f"NFRs: {', '.join(task.nfrs)}")
            if task.references.code:
                print(f"Code: {', '.join(task.references.code)}")
            if task.verification.command:
                print(f"Verification: {task.verification.command}")
                print(f"Status: {task.verification.status.value}")

    except Exception as e:
        print_error(f"Failed to read task: {e}")
        sys.exit(1)


def cmd_edit(args):
    """Edit a task in $EDITOR."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result
    _open_in_editor(path)


def cmd_promote(args):
    """Move task forward in workflow."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result

    # Determine target status
    workflow = [TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                TaskStatus.REVIEW, TaskStatus.DONE]

    if args.target_status:
        target_status = TaskStatus(args.target_status)
    else:
        # Next in workflow
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_info(f"Task {args.task_id} is already at final status: {current_status.value}")
            return
        target_status = workflow[current_idx + 1]

    # Move task
    _move_task(storage, args.task_id, path, target_status)


def cmd_move(args):
    """Move task to specific status."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result
    target_status = TaskStatus(args.status)

    _move_task(storage, args.task_id, path, target_status)


def cmd_kanban(args):
    """Display kanban board."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Group tasks by status
    tasks_by_status = {}
    for status in [TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                   TaskStatus.REVIEW, TaskStatus.DONE]:
        tasks_by_status[status] = []

    # Read all tasks from manifest
    manifest_rows = _read_manifest(storage)
    for row in manifest_rows:
        if args.epic and row['epic'] != args.epic.upper():
            continue

        status = TaskStatus(row['status'])
        if status in tasks_by_status:
            tasks_by_status[status].append(row)

    # Display columns
    for status in [TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                   TaskStatus.REVIEW, TaskStatus.DONE]:
        display_kanban_column(status.value, tasks_by_status[status])


def cmd_verify(args):
    """Run verification tests for a task."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result

    try:
        task = storage.read_task_file(path)

        if not task.verification.command:
            print_warning(
                f"No verification command set for {args.task_id}\n"
                f"Use: taskpy link {args.task_id} --verify 'cargo test feature::test'"
            )
            sys.exit(1)

        print_info(f"Running verification: {task.verification.command}")

        # Run command
        result = subprocess.run(
            task.verification.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print_success("Verification passed")
            if args.update:
                task.verification.status = task.models.VerificationStatus.PASSED
                task.verification.last_run = datetime.utcnow()
                storage.write_task_file(task)
        else:
            print_error(f"Verification failed\n\nOutput:\n{result.stdout}\n{result.stderr}")
            if args.update:
                task.verification.status = task.models.VerificationStatus.FAILED
                task.verification.last_run = datetime.utcnow()
                task.verification.output = result.stderr
                storage.write_task_file(task)
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print_error("Verification timed out (300s)")
        sys.exit(1)
    except Exception as e:
        print_error(f"Verification error: {e}")
        sys.exit(1)


def cmd_epics(args):
    """List available epics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    epics = storage.load_epics()

    headers = ["Epic", "Description", "Active", "Budget"]
    rows = [
        [
            name,
            epic.description[:50],
            "✓" if epic.active else "✗",
            str(epic.story_point_budget) if epic.story_point_budget else "-"
        ]
        for name, epic in sorted(epics.items())
    ]

    rolo_table(headers, rows, f"Available Epics ({len(epics)})")


def cmd_nfrs(args):
    """List NFRs."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    nfrs = storage.load_nfrs()

    if args.defaults:
        nfrs = {nfr_id: nfr for nfr_id, nfr in nfrs.items() if nfr.default}

    for nfr_id, nfr in sorted(nfrs.items()):
        default_marker = " [DEFAULT]" if nfr.default else ""
        print(f"{nfr_id}{default_marker}: {nfr.title}")
        print(f"  {nfr.description}")
        if nfr.verification:
            print(f"  Verification: {nfr.verification}")
        print()


def cmd_link(args):
    """Link references to a task."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result

    try:
        task = storage.read_task_file(path)

        # Add references
        if args.code:
            task.references.code.extend(args.code)
        if args.docs:
            task.references.docs.extend(args.docs)
        if args.plan:
            task.references.plans.extend(args.plan)
        if args.test:
            task.references.tests.extend(args.test)
        if args.nfr:
            task.nfrs.extend(args.nfr)

        # Save
        storage.write_task_file(task)

        print_success(f"References linked to {args.task_id}")

    except Exception as e:
        print_error(f"Failed to link references: {e}")
        sys.exit(1)


def cmd_session(args):
    """Manage work sessions."""
    # TODO: Implement session management
    print_info("Session management coming soon in META PROCESS v4")


def cmd_stats(args):
    """Show task statistics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest
    rows = _read_manifest(storage)

    if args.epic:
        rows = [r for r in rows if r['epic'] == args.epic.upper()]

    # Calculate stats
    total = len(rows)
    by_status = {}
    by_priority = {}
    total_sp = 0

    for row in rows:
        status = row['status']
        priority = row['priority']
        sp = int(row['story_points'])

        by_status[status] = by_status.get(status, 0) + 1
        by_priority[priority] = by_priority.get(priority, 0) + 1
        total_sp += sp

    # Display
    print(f"\n{'='*50}")
    print(f"Task Statistics")
    if args.epic:
        print(f"Epic: {args.epic.upper()}")
    print(f"{'='*50}\n")

    print(f"Total Tasks: {total}")
    print(f"Total Story Points: {total_sp}\n")

    print("By Status:")
    for status, count in sorted(by_status.items()):
        print(f"  {status:15} {count:3}")

    print("\nBy Priority:")
    for priority, count in sorted(by_priority.items()):
        print(f"  {priority:15} {count:3}")

    print()


# Helper functions

def _open_in_editor(path: Path):
    """Open file in $EDITOR."""
    editor = os.environ.get('EDITOR', 'vi')
    subprocess.run([editor, str(path)])


def _move_task(storage: TaskStorage, task_id: str, current_path: Path, target_status: TaskStatus):
    """Move a task to a new status."""
    try:
        # Read task
        task = storage.read_task_file(current_path)

        # Update status
        old_status = task.status
        task.status = target_status

        # Delete old file
        current_path.unlink()

        # Write to new location
        storage.write_task_file(task)

        print_success(
            f"Moved {task_id}: {old_status.value} → {target_status.value}",
            "Task Moved"
        )

    except Exception as e:
        print_error(f"Failed to move task: {e}")
        sys.exit(1)


def _read_manifest(storage: TaskStorage):
    """Read all rows from manifest."""
    import csv

    rows = []
    with open(storage.manifest_file, 'r', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            rows.append(row)
    return rows


def _read_manifest_with_filters(storage: TaskStorage, args):
    """Read manifest and apply filters."""
    rows = _read_manifest(storage)

    # Apply filters
    if hasattr(args, 'epic') and args.epic:
        rows = [r for r in rows if r['epic'] == args.epic.upper()]

    if hasattr(args, 'status') and args.status:
        rows = [r for r in rows if r['status'] == args.status]

    if hasattr(args, 'priority') and args.priority:
        rows = [r for r in rows if r['priority'] == args.priority]

    if hasattr(args, 'assigned') and args.assigned:
        rows = [r for r in rows if r['assigned'] == args.assigned]

    if hasattr(args, 'tags') and args.tags:
        filter_tags = set(t.strip() for t in args.tags.split(','))
        rows = [r for r in rows if filter_tags.intersection(r['tags'].split(','))]

    return rows
