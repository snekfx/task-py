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


# Gate Validation Functions

def validate_stub_to_backlog(task: Task) -> tuple[bool, list[str]]:
    """
    Validate stub → backlog promotion.

    Requirements:
    - Task must have content (body)
    - Must have story points

    Returns:
        (is_valid, list of blockers)
    """
    blockers = []

    if not task.content or len(task.content.strip()) < 20:
        blockers.append("Task needs description (minimum 20 characters)")

    if task.story_points == 0:
        blockers.append("Task needs story points estimation")

    return (len(blockers) == 0, blockers)


def validate_in_progress_to_qa(task: Task) -> tuple[bool, list[str]]:
    """
    Validate in_progress → qa promotion.

    Requirements:
    - Must have code references
    - Must have test references
    - Verification must pass (if configured)

    Returns:
        (is_valid, list of blockers)
    """
    blockers = []

    if not task.references.code:
        blockers.append("Task needs code references (use: taskpy link TASK-ID --code path/to/file.py)")

    if not task.references.tests:
        blockers.append("Task needs test references (use: taskpy link TASK-ID --test path/to/test.py)")

    # Check verification if command is set
    if task.verification.command:
        from taskpy.models import VerificationStatus
        if task.verification.status != VerificationStatus.PASSED:
            blockers.append(f"Verification must pass (status: {task.verification.status.value})")

    return (len(blockers) == 0, blockers)


def validate_qa_to_done(task: Task) -> tuple[bool, list[str]]:
    """
    Validate qa → done promotion.

    Requirements:
    - Must have commit hash

    Returns:
        (is_valid, list of blockers)
    """
    blockers = []

    if not task.commit_hash:
        blockers.append("Task needs commit hash (use: taskpy promote TASK-ID --commit HASH)")

    return (len(blockers) == 0, blockers)


def validate_done_demotion(task: Task, reason: Optional[str]) -> tuple[bool, list[str]]:
    """
    Validate demotion from done status.

    Requirements:
    - Must provide reason

    Returns:
        (is_valid, list of blockers)
    """
    blockers = []

    if not reason:
        blockers.append("Demotion from 'done' requires --reason flag")

    return (len(blockers) == 0, blockers)


def validate_promotion(task: Task, target_status: TaskStatus, commit_hash: Optional[str] = None) -> tuple[bool, list[str]]:
    """
    Validate task promotion based on current and target status.

    Args:
        task: Task to validate
        target_status: Target status
        commit_hash: Optional commit hash (for qa→done)

    Returns:
        (is_valid, list of blockers)
    """
    current = task.status

    # stub → backlog
    if current == TaskStatus.STUB and target_status == TaskStatus.BACKLOG:
        return validate_stub_to_backlog(task)

    # in_progress → qa
    elif current == TaskStatus.IN_PROGRESS and target_status == TaskStatus.QA:
        return validate_in_progress_to_qa(task)

    # qa → done
    elif current == TaskStatus.QA and target_status == TaskStatus.DONE:
        # Temporarily set commit_hash for validation
        original_hash = task.commit_hash
        if commit_hash:
            task.commit_hash = commit_hash
        result = validate_qa_to_done(task)
        task.commit_hash = original_hash
        return result

    # No gates for other transitions
    return (True, [])


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

    # Validate milestone if provided
    milestone = None
    if hasattr(args, 'milestone') and args.milestone:
        milestones = storage.load_milestones()
        if args.milestone not in milestones:
            print_warning(
                f"Milestone '{args.milestone}' not found.\n"
                f"Available: {', '.join(milestones.keys())}\n"
                f"Task will be created without milestone assignment."
            )
        else:
            milestone = args.milestone

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
        milestone=milestone,
        content=f"# {title}\n\n## Description\n\n<!-- Add task description here -->\n\n## Acceptance Criteria\n\n- [ ] Criterion 1\n- [ ] Criterion 2\n\n## Notes\n\n<!-- Add notes here -->\n"
    )

    # Apply default NFRs
    nfrs = storage.load_nfrs()
    default_nfrs = [nfr_id for nfr_id, nfr in nfrs.items() if nfr.default]
    task.nfrs = default_nfrs

    # Save task
    try:
        storage.write_task_file(task)
        task_path = storage.get_task_path(task_id, task.status)
        milestone_info = f"Milestone: {milestone}\n" if milestone else ""

        # Show gate requirements for next promotion
        workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                    TaskStatus.QA, TaskStatus.DONE]
        current_idx = workflow.index(task.status)
        gate_info = ""
        if current_idx < len(workflow) - 1:
            next_status = workflow[current_idx + 1]
            is_valid, blockers = validate_promotion(task, next_status, None)
            if not is_valid:
                gate_info = f"\nGate Requirements for {task.status.value} → {next_status.value}:\n"
                for blocker in blockers:
                    gate_info += f"  • {blocker}\n"

        print_success(
            f"Created task: {task_id}\n"
            f"Title: {title}\n"
            f"Epic: {epic_name}\n"
            f"Status: {args.status}\n"
            f"Story Points: {args.story_points}\n"
            f"Priority: {args.priority}\n"
            f"{milestone_info}"
            f"Default NFRs: {len(default_nfrs)}\n"
            f"File: {task_path}\n"
            f"{gate_info}\n"
            f"View: taskpy show {task_id}\n"
            f"Edit: taskpy edit {task_id}",
            f"Task {task_id} Created"
        )

        # Open in editor if requested
        if args.edit:
            _open_in_editor(task_path)

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

    # Read task for validation
    task = storage.read_task_file(path)

    # Determine target status
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                TaskStatus.QA, TaskStatus.DONE]

    if hasattr(args, 'target_status') and args.target_status:
        target_status = TaskStatus(args.target_status)
    else:
        # Next in workflow
        current_idx = workflow.index(current_status)
        if current_idx >= len(workflow) - 1:
            print_info(f"Task {args.task_id} is already at final status: {current_status.value}")
            return
        target_status = workflow[current_idx + 1]

    # Validate promotion gates
    commit_hash = getattr(args, 'commit', None)
    is_valid, blockers = validate_promotion(task, target_status, commit_hash)

    if not is_valid:
        print_error(f"Cannot promote {args.task_id}: {current_status.value} → {target_status.value}")
        print()
        print("❌ Blockers:")
        for blocker in blockers:
            print(f"  • {blocker}")
        sys.exit(1)

    # Set commit_hash if provided
    if commit_hash:
        task.commit_hash = commit_hash

    # Move task
    _move_task(storage, args.task_id, path, target_status, task)


def cmd_demote(args):
    """Move task backwards in workflow with required reason."""
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
    task = storage.read_task_file(path)

    # Validate demotion from done requires reason
    if current_status == TaskStatus.DONE:
        is_valid, blockers = validate_done_demotion(task, args.reason)
        if not is_valid:
            print_error(f"Cannot demote {args.task_id} from done")
            print()
            print("❌ Blockers:")
            for blocker in blockers:
                print(f"  • {blocker}")
            sys.exit(1)
        task.demotion_reason = args.reason

    # Determine target status (previous in workflow)
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                TaskStatus.QA, TaskStatus.DONE]

    if hasattr(args, 'to') and args.to:
        target_status = TaskStatus(args.to)
    else:
        # Previous in workflow
        current_idx = workflow.index(current_status)
        if current_idx <= 0:
            print_info(f"Task {args.task_id} is already at initial status: {current_status.value}")
            return
        target_status = workflow[current_idx - 1]

    # Move task
    _move_task(storage, args.task_id, path, target_status, task)


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


def cmd_info(args):
    """Show task status and gate requirements for next promotion."""
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
    task = storage.read_task_file(path)

    # Determine next status in workflow
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                TaskStatus.QA, TaskStatus.DONE]

    print_info(f"Task: {args.task_id}")
    print(f"Current Status: {current_status.value}")
    print(f"Title: {task.title}")
    print()

    current_idx = workflow.index(current_status)
    if current_idx >= len(workflow) - 1:
        print_success("Task is at final status (done)")
        return

    next_status = workflow[current_idx + 1]
    print(f"Next Status: {next_status.value}")
    print()

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        print_success("✅ Ready to promote - all requirements met")
    else:
        print("Gate Requirements:")
        for blocker in blockers:
            print(f"  • {blocker}")


def cmd_stoplight(args):
    """Validate gate requirements and exit with status code."""
    storage = get_storage()

    if not storage.is_initialized():
        sys.exit(2)  # Blocked

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        sys.exit(2)  # Blocked

    path, current_status = result
    task = storage.read_task_file(path)

    # Determine next status in workflow
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                TaskStatus.QA, TaskStatus.DONE]

    current_idx = workflow.index(current_status)
    if current_idx >= len(workflow) - 1:
        # Task is done
        sys.exit(0)  # Ready (no more promotions)

    next_status = workflow[current_idx + 1]

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        # Ready to promote
        sys.exit(0)
    elif task.status == TaskStatus.BLOCKED:
        # Blocked status
        sys.exit(2)
    else:
        # Missing requirements
        sys.exit(1)


def cmd_kanban(args):
    """Display kanban board."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Group tasks by status
    tasks_by_status = {}
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                   TaskStatus.QA, TaskStatus.DONE]:
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
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.IN_PROGRESS,
                   TaskStatus.QA, TaskStatus.DONE]:
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


def cmd_tour(args):
    """Display TaskPy quick reference tour."""
    tour_text = """
==================================================
TaskPy Quick Reference Tour
==================================================

GETTING STARTED
---------------
  taskpy init                           Initialize TaskPy in current project
  taskpy create EPIC "title" --sp N     Create a task with story points
  taskpy create FEAT "feature" --milestone milestone-1  Create with milestone

DAILY WORKFLOW
--------------
  taskpy list                           List all tasks
  taskpy list --epic FEAT               Filter by epic
  taskpy list --status backlog          Filter by status
  taskpy list --sprint                  Show sprint tasks only

  taskpy show TASK-ID                   View task details
  taskpy edit TASK-ID                   Edit task in $EDITOR

  taskpy promote TASK-ID                Move task forward in workflow
  taskpy move TASK-ID done              Jump to specific status

SPRINT MANAGEMENT
-----------------
  taskpy sprint add TASK-ID             Add task to current sprint
  taskpy sprint remove TASK-ID          Remove from sprint
  taskpy sprint list                    List sprint tasks
  taskpy sprint clear                   Clear entire sprint
  taskpy sprint stats                   Sprint statistics

MILESTONE TRACKING
------------------
  taskpy milestones                     List all milestones (by priority)
  taskpy milestone show milestone-1     Show milestone progress
  taskpy milestone assign TASK-ID milestone-1  Assign task
  taskpy milestone start milestone-2    Mark milestone as active
  taskpy milestone complete milestone-1 Mark milestone done

QUERYING & STATS
----------------
  taskpy list --format ids              List task IDs only
  taskpy list --format tsv              TSV output for scripting
  taskpy stats                          Project statistics
  taskpy stats --epic FEAT              Epic-specific stats
  taskpy stats --milestone milestone-1  Milestone stats
  taskpy kanban                         Kanban board view
  taskpy kanban --epic FEAT             Epic-specific kanban

REFERENCE LINKING
-----------------
  taskpy link TASK-ID --code src/foo.py         Link source file
  taskpy link TASK-ID --test tests/test_foo.py  Link test file
  taskpy link TASK-ID --verify "pytest tests/"  Set verification command
  taskpy verify TASK-ID --update                Run and update verification

WORKFLOW STATUSES
-----------------
  stub → backlog → ready → in_progress → qa → done → archived

  stub         Incomplete, needs grooming
  backlog      Groomed, ready for work
  ready        Selected for sprint
  in_progress  Actively being developed
  qa           In testing/review
  done         Completed
  archived     Long-term storage
  blocked      Blocked by dependencies (special state)

USEFUL FLAGS
------------
  --view=data                           Plain output (no boxy formatting)
  --no-boxy                             Same as --view=data
  --priority critical|high|medium|low   Set task priority
  --milestone milestone-N               Assign to milestone
  --sp N                                Set story points

CONFIGURATION
-------------
  data/kanban/info/epics.toml           Epic definitions
  data/kanban/info/nfrs.toml            Non-functional requirements
  data/kanban/info/milestones.toml      Milestone definitions
  data/kanban/info/config.toml          TaskPy configuration

TIPS
----
  • Tasks stored as markdown in data/kanban/status/
  • Git-friendly: commit config/, ignore task data
  • Use --view=data for scripting/automation
  • Sprint = session-scoped work queue
  • Milestones = multi-phase project organization

==================================================
"""
    print(tour_text)


def cmd_sprint(args):
    """Route sprint subcommands."""
    subcommand_handlers = {
        'add': _cmd_sprint_add,
        'remove': _cmd_sprint_remove,
        'list': _cmd_sprint_list,
        'clear': _cmd_sprint_clear,
        'stats': _cmd_sprint_stats,
    }

    handler = subcommand_handlers.get(args.sprint_command)
    if handler:
        handler(args)
    else:
        print_error(f"Unknown sprint command: {args.sprint_command}")
        sys.exit(1)


def _cmd_sprint_add(args):
    """Add task to sprint."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_id = args.task_id.upper()

    # Find task
    result = storage.find_task_file(task_id)
    if not result:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    path, status = result
    task = storage.read_task_file(path)

    # Check if already in sprint
    if task.in_sprint:
        print_warning(f"{task_id} is already in the sprint")
        return

    # Add to sprint
    task.in_sprint = True
    task.updated = datetime.utcnow()
    storage.write_task_file(task)

    print_success(f"Added {task_id} to sprint")


def _cmd_sprint_remove(args):
    """Remove task from sprint."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    task_id = args.task_id.upper()

    # Find task
    result = storage.find_task_file(task_id)
    if not result:
        print_error(f"Task not found: {task_id}")
        sys.exit(1)

    path, status = result
    task = storage.read_task_file(path)

    # Check if in sprint
    if not task.in_sprint:
        print_warning(f"{task_id} is not in the sprint")
        return

    # Remove from sprint
    task.in_sprint = False
    task.updated = datetime.utcnow()
    storage.write_task_file(task)

    print_success(f"Removed {task_id} from sprint")


def _cmd_sprint_list(args):
    """List all tasks in sprint."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and filter sprint tasks
    rows = _read_manifest(storage)
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Display tasks as table
    headers = ["ID", "Title", "Status", "SP", "Priority"]
    table_rows = [
        [
            task['id'],
            task['title'][:50],  # Truncate long titles
            task['status'],
            task['story_points'],
            task['priority']
        ]
        for task in sprint_tasks
    ]
    rolo_table(headers, table_rows, f"Sprint Tasks ({len(sprint_tasks)} found)")


def _cmd_sprint_clear(args):
    """Clear all tasks from sprint."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and find all sprint tasks
    rows = _read_manifest(storage)
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Remove all tasks from sprint
    for row in sprint_tasks:
        result = storage.find_task_file(row['id'])
        if result:
            path, status = result
            task = storage.read_task_file(path)
            task.in_sprint = False
            task.updated = datetime.utcnow()
            storage.write_task_file(task)

    print_success(f"Cleared {len(sprint_tasks)} tasks from sprint")


def _cmd_sprint_stats(args):
    """Show sprint statistics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and filter sprint tasks
    rows = _read_manifest(storage)
    sprint_tasks = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    if not sprint_tasks:
        print_info("No tasks in sprint")
        return

    # Calculate statistics
    total_tasks = len(sprint_tasks)
    total_sp = sum(int(r.get('story_points', 0)) for r in sprint_tasks)

    # Group by status
    by_status = {}
    for row in sprint_tasks:
        status = row.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1

    # Group by priority
    by_priority = {}
    for row in sprint_tasks:
        priority = row.get('priority', 'unknown')
        by_priority[priority] = by_priority.get(priority, 0) + 1

    # Display statistics
    print(f"\n{'='*50}")
    print(f"Sprint Statistics")
    print(f"{'='*50}\n")

    print(f"Total Tasks: {total_tasks}")
    print(f"Total Story Points: {total_sp}\n")

    print("By Status:")
    for status in ['stub', 'backlog', 'ready', 'in_progress', 'qa', 'done', 'blocked']:
        count = by_status.get(status, 0)
        if count > 0:
            print(f"  {status:15} {count:3}")

    print("\nBy Priority:")
    for priority in ['critical', 'high', 'medium', 'low']:
        count = by_priority.get(priority, 0)
        if count > 0:
            print(f"  {priority:15} {count:3}")

    print()


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

    if hasattr(args, 'milestone') and args.milestone:
        rows = [r for r in rows if r.get('milestone') == args.milestone]

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


def _move_task(storage: TaskStorage, task_id: str, current_path: Path, target_status: TaskStatus, task: Optional[Task] = None):
    """Move a task to a new status."""
    try:
        # Read task if not provided
        if task is None:
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

    if hasattr(args, 'milestone') and args.milestone:
        rows = [r for r in rows if r.get('milestone') == args.milestone]

    if hasattr(args, 'sprint') and args.sprint:
        rows = [r for r in rows if r.get('in_sprint', 'false') == 'true']

    return rows


def cmd_milestones(args):
    """List all milestones sorted by priority."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    milestones = storage.load_milestones()

    if not milestones:
        print_info("No milestones defined. Add them to: data/kanban/info/milestones.toml")
        return

    # Sort by priority
    sorted_milestones = sorted(milestones.items(), key=lambda x: x[1].priority)

    # Display
    print("==================================================")
    print("Milestones (sorted by priority)")
    print("==================================================\n")

    for milestone_id, m in sorted_milestones:
        status_color = {
            'active': '🟢',
            'planned': '⚪',
            'blocked': '🔴',
            'completed': '✅'
        }.get(m.status, '⚪')

        print(f"{status_color} [{milestone_id}] {m.name}")
        print(f"   Priority: {m.priority} | Status: {m.status}")
        if m.goal_sp:
            print(f"   Goal: {m.goal_sp} SP")
        print(f"   {m.description}")
        if m.blocked_reason:
            print(f"   ⚠️  Blocked: {m.blocked_reason}")
        print()


def cmd_milestone(args):
    """Route milestone subcommands."""
    if not args.milestone_command:
        print_error("Please specify a milestone subcommand: show, start, complete, assign")
        sys.exit(1)

    # Route to subcommand handler
    subcommand_handlers = {
        'show': _cmd_milestone_show,
        'start': _cmd_milestone_start,
        'complete': _cmd_milestone_complete,
        'assign': _cmd_milestone_assign,
    }

    handler = subcommand_handlers.get(args.milestone_command)
    if handler:
        handler(args)
    else:
        print_error(f"Unknown milestone subcommand: {args.milestone_command}")
        sys.exit(1)


def _cmd_milestone_show(args):
    """Show milestone details and task statistics."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Load milestone
    milestones = storage.load_milestones()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    # Get tasks for this milestone
    rows = _read_manifest(storage)
    milestone_tasks = [r for r in rows if r.get('milestone') == args.milestone_id]

    # Calculate stats
    total_tasks = len(milestone_tasks)
    total_sp = sum(int(r['story_points']) for r in milestone_tasks)
    completed_tasks = [r for r in milestone_tasks if r['status'] in ['done', 'archived']]
    completed_sp = sum(int(r['story_points']) for r in completed_tasks)
    remaining_sp = total_sp - completed_sp

    # Group by status
    by_status = {}
    for task in milestone_tasks:
        status = task['status']
        by_status[status] = by_status.get(status, 0) + 1

    # Display
    status_emoji = {
        'active': '🟢',
        'planned': '⚪',
        'blocked': '🔴',
        'completed': '✅'
    }.get(milestone.status, '⚪')

    print(f"\n{status_emoji} {milestone.name}")
    print(f"{'='*60}")
    print(f"ID: {args.milestone_id}")
    print(f"Priority: {milestone.priority}")
    print(f"Status: {milestone.status}")
    if milestone.goal_sp:
        print(f"Goal: {milestone.goal_sp} SP")
    print(f"\n{milestone.description}\n")

    if milestone.blocked_reason:
        print(f"⚠️  Blocked: {milestone.blocked_reason}\n")

    print(f"Task Progress:")
    print(f"  Total Tasks: {total_tasks}")
    print(f"  Completed: {len(completed_tasks)} / {total_tasks}")
    print(f"  Story Points: {completed_sp} / {total_sp} completed ({remaining_sp} remaining)")
    if milestone.goal_sp:
        progress_pct = (completed_sp / milestone.goal_sp * 100) if milestone.goal_sp > 0 else 0
        print(f"  Goal Progress: {progress_pct:.1f}%")

    if by_status:
        print(f"\nBy Status:")
        for status, count in sorted(by_status.items()):
            print(f"  {status:15} {count:3}")

    print()


def _cmd_milestone_start(args):
    """Mark milestone as active."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Load milestones
    milestones = storage.load_milestones()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    if milestone.status == 'active':
        print_info(f"Milestone {args.milestone_id} is already active")
        return

    # Update status in TOML file
    _update_milestone_status(storage, args.milestone_id, 'active')

    print_success(
        f"Milestone {args.milestone_id} marked as active\n"
        f"Name: {milestone.name}",
        "Milestone Started"
    )


def _cmd_milestone_complete(args):
    """Mark milestone as completed."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Load milestones
    milestones = storage.load_milestones()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    milestone = milestones[args.milestone_id]

    if milestone.status == 'completed':
        print_info(f"Milestone {args.milestone_id} is already completed")
        return

    # Check if all tasks are done
    rows = _read_manifest(storage)
    milestone_tasks = [r for r in rows if r.get('milestone') == args.milestone_id]
    incomplete = [r for r in milestone_tasks if r['status'] not in ['done', 'archived']]

    if incomplete:
        print_warning(
            f"Milestone has {len(incomplete)} incomplete tasks:\n" +
            "\n".join(f"  - {t['id']}: {t['title']}" for t in incomplete[:5])
        )
        if len(incomplete) > 5:
            print_warning(f"  ... and {len(incomplete) - 5} more")
        print_warning("\nMarking as completed anyway.")

    # Update status in TOML file
    _update_milestone_status(storage, args.milestone_id, 'completed')

    print_success(
        f"Milestone {args.milestone_id} marked as completed\n"
        f"Name: {milestone.name}",
        "Milestone Completed"
    )


def _cmd_milestone_assign(args):
    """Assign task to milestone."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Validate milestone exists
    milestones = storage.load_milestones()
    if args.milestone_id not in milestones:
        print_error(f"Milestone not found: {args.milestone_id}")
        sys.exit(1)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, status = result

    try:
        # Read task
        task = storage.read_task_file(path)
        old_milestone = task.milestone

        # Update milestone
        task.milestone = args.milestone_id

        # Save task
        storage.write_task_file(task)

        if old_milestone:
            print_success(
                f"Moved {args.task_id} from {old_milestone} to {args.milestone_id}",
                "Task Reassigned"
            )
        else:
            print_success(
                f"Assigned {args.task_id} to {args.milestone_id}",
                "Task Assigned"
            )

    except Exception as e:
        print_error(f"Failed to assign task: {e}")
        sys.exit(1)


def _update_milestone_status(storage: TaskStorage, milestone_id: str, new_status: str):
    """Update milestone status in TOML file."""
    import re

    milestones_file = storage.info_dir / "milestones.toml"
    content = milestones_file.read_text()

    # Find the milestone section and update status
    # Pattern: [milestone-id]\n... status = "old_status" ... next [section or EOF
    pattern = rf'(\[{re.escape(milestone_id)}\][^\[]*status\s*=\s*")[^"]*(")'
    replacement = rf'\g<1>{new_status}\g<2>'

    updated_content = re.sub(pattern, replacement, content)

    if updated_content == content:
        # If pattern didn't match, milestone might not have a status field
        # Try to add it after the milestone header
        pattern = rf'(\[{re.escape(milestone_id)}\]\n)'
        if re.search(pattern, content):
            replacement = rf'\g<1>status = "{new_status}"\n'
            updated_content = re.sub(pattern, replacement, content, count=1)

    milestones_file.write_text(updated_content)
