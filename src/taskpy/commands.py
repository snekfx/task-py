"""
Command implementations for TaskPy.

Each command is implemented as cmd_<name>(args) function.
"""

import os
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Iterable, Tuple

from taskpy.models import Task, TaskStatus, Priority, TaskReference, Verification, VerificationStatus, utc_now
from taskpy.storage import TaskStorage, StorageError
from taskpy.output import (
    print_success, print_error, print_info, print_warning,
    display_task_card, display_kanban_column, rolo_table,
    get_output_mode, OutputMode
)


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def parse_task_ids(raw_ids: List[str]) -> List[str]:
    """
    Parse task IDs from user input - supports both space-separated and comma-delimited.

    Args:
        raw_ids: List of raw ID strings (from argparse nargs='+')
                 Can contain: ["FEAT-01", "FEAT-02"] or ["FEAT-01,FEAT-02"] or ["FEAT-01, FEAT-02"]

    Returns:
        List of normalized task IDs (uppercase, deduplicated, order preserved)

    Example:
        parse_task_ids(["FEAT-01,FEAT-02", "BUGS-03"])
        # Returns: ["FEAT-01", "FEAT-02", "BUGS-03"]
    """
    task_ids = []
    for item in raw_ids:
        # Split on comma if present
        if ',' in item:
            task_ids.extend([tid.strip().upper() for tid in item.split(',') if tid.strip()])
        else:
            task_ids.append(item.strip().upper())

    # Remove duplicates while preserving order
    seen = set()
    return [tid for tid in task_ids if tid not in seen and not seen.add(tid)]


def log_override(storage: TaskStorage, task_id: str, from_status: str, to_status: str, reason: Optional[str] = None):
    """Log override event to override_log.txt."""
    log_file = storage.info_dir / "override_log.txt"
    timestamp = utc_now().strftime("%Y-%m-%dT%H:%M:%S")
    reason_str = f" | Reason: {reason}" if reason else ""

    log_entry = f"{timestamp} | {task_id} | {from_status}→{to_status}{reason_str}\n"

    with open(log_file, "a") as f:
        f.write(log_entry)


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


def validate_active_to_qa(task: Task) -> tuple[bool, list[str]]:
    """
    Validate active → qa promotion.

    Requirements:
    - Must have code/doc references
    - Must have test references (unless DOCS* epic)
    - Must have verification command set (unless DOCS* epic)
    - Verification must pass

    Returns:
        (is_valid, list of blockers)
    """
    blockers = []

    # Check if this is a DOCS task
    is_docs_task = task.epic_prefix.startswith('DOCS')

    if not task.references.code and not task.references.docs:
        blockers.append("Task needs code or doc references (use: taskpy link TASK-ID --code path/to/file.py or --docs path/to/doc.md)")

    # DOCS tasks don't need test references or verification
    if not is_docs_task:
        if not task.references.tests:
            blockers.append("Task needs test references (use: taskpy link TASK-ID --test path/to/test.py)")

        # Check verification command is set and has passed
        if not task.verification.command:
            blockers.append("Task needs verification command (use: taskpy link TASK-ID --verify \"test command\")")
        else:
            from taskpy.models import VerificationStatus
            if task.verification.status != VerificationStatus.PASSED:
                blockers.append(f"Verification must pass (status: {task.verification.status.value}). Run: taskpy verify {task.id} --update")
    else:
        # DOCS tasks should have doc references
        if not task.references.docs:
            blockers.append("DOCS task needs doc references (use: taskpy link TASK-ID --docs path/to/doc.md)")

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

    # Check if task is blocked
    if current == TaskStatus.BLOCKED:
        reason = task.blocked_reason or "No reason provided"
        return (False, [f"Task is blocked: {reason}. Use 'taskpy unblock {task.id}' to unblock."])

    # stub → backlog
    if current == TaskStatus.STUB and target_status == TaskStatus.BACKLOG:
        return validate_stub_to_backlog(task)

    # active → qa
    elif current == TaskStatus.ACTIVE and target_status == TaskStatus.QA:
        return validate_active_to_qa(task)

    # regression → qa (re-review after fixes)
    elif current == TaskStatus.REGRESSION and target_status == TaskStatus.QA:
        return validate_active_to_qa(task)  # Same requirements as active → qa

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
        # Get explicit type from args if provided
        project_type = getattr(args, 'type', None)

        # Initialize with project type detection
        detected_type, auto_detected = storage.initialize(
            force=args.force,
            project_type=project_type
        )

        # Build project type message
        if auto_detected:
            type_msg = f"  • Project type: {detected_type} (auto-detected)\n"
        else:
            type_msg = f"  • Project type: {detected_type} (explicitly set)\n"

        print_success(
            f"TaskPy initialized at: {storage.kanban}\n\n"
            f"Structure created:\n"
            f"  • data/kanban/info/     - Configuration (epics, NFRs)\n"
            f"  • data/kanban/status/   - Task files by status\n"
            f"  • data/kanban/manifest.tsv - Fast query index\n"
            f"  • .gitignore            - Updated to exclude kanban data\n"
            f"{type_msg}\n"
            f"Next steps:\n"
            f"  1. Review config: data/kanban/info/config.toml\n"
            f"  2. Review epics: data/kanban/info/epics.toml\n"
            f"  3. Review NFRs: data/kanban/info/nfrs.toml\n"
            f"  4. Create your first task: taskpy create FEAT \"Your feature\"\n",
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

    # Generate content template or use provided body
    provided_body = getattr(args, 'body', None)
    if provided_body:
        body_text = provided_body.replace("\\n", "\n").strip()
        if not body_text:
            body_text = "<!-- Add task description here -->"
    else:
        body_text = ""

    description_section = (
        f"## Description\n\n{body_text}\n\n"
        if body_text
        else "## Description\n\n<!-- Add task description here -->\n\n"
    )

    content = (
        f"# {title}\n\n"
        f"{description_section}"
        "## Acceptance Criteria\n\n"
        "- [ ] Criterion 1\n"
        "- [ ] Criterion 2\n\n"
        "## Notes\n\n"
        "<!-- Add notes here -->\n"
    )

    wants_stub = getattr(args, 'stub', False)
    if wants_stub:
        args.status = 'stub'
    if args.status != "stub" and not wants_stub:
        if not body_text:
            print_error(
                "Backlog-ready tasks require --body unless you pass --stub to acknowledge a skeletal ticket."
            )
            sys.exit(1)

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
        content=content
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
        workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
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

        grooming_msg = (
            "Next steps:\n"
            f"  1. Open {task_path} (or run: taskpy edit {task_id}) and expand the Description,"
            " Acceptance Criteria, and Notes with the latest discovery or requirement details.\n"
            f"  2. Capture reproduction steps / implementation notes directly in the markdown so"
            " agents have context.\n"
            f"  3. Use `taskpy link {task_id}` to attach code, docs, plans, and verification commands"
            " when they are known.\n"
        )

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
            f"{grooming_msg}"
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
        headers = ["ID", "Epic", "#", "Title", "Status", "SP", "Priority", "Sprint"]
        rows = [_manifest_row_to_table(task) for task in tasks]
        row_statuses = [task.get('status') for task in tasks]
        rolo_table(headers, rows, f"Tasks ({len(tasks)} found)", row_statuses=row_statuses)


def cmd_show(args):
    """Display one or more tasks."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Parse task IDs - support both space-separated and comma-delimited
    task_ids = parse_task_ids(args.task_ids)

    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    # Collect all tasks
    tasks_to_display = []
    for task_id in task_ids:
        result = storage.find_task_file(task_id)
        if not result:
            print_error(f"Task not found: {task_id}")
            continue

        path, status = result
        try:
            task = storage.read_task_file(path)
            tasks_to_display.append(task)
        except Exception as e:
            print_error(f"Failed to read task {task_id}: {e}")
            continue

    if not tasks_to_display:
        print_error("No valid tasks to display")
        sys.exit(1)

    # Display tasks
    for i, task in enumerate(tasks_to_display):
        # Add divider between tasks (except before first)
        if i > 0:
            if get_output_mode() == OutputMode.DATA:
                print("\n" + "=" * 80 + "\n")
            else:
                print()  # Just blank line in boxy mode (boxy handles dividers)

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
            if task.resolution:
                print(f"\nResolution: {task.resolution.value}")
                print(f"Reason: {task.resolution_reason}")
                if task.duplicate_of:
                    print(f"Duplicate of: {task.duplicate_of}")


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
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                TaskStatus.QA, TaskStatus.DONE]

    if hasattr(args, 'target_status') and args.target_status:
        target_status = TaskStatus(args.target_status)
    else:
        # Special case: REGRESSION promotes back to QA for re-review
        if current_status == TaskStatus.REGRESSION:
            target_status = TaskStatus.QA
            print_info(f"Re-submitting {args.task_id} from regression to QA for review")
        else:
            # Normal workflow: next in workflow
            current_idx = workflow.index(current_status)
            if current_idx >= len(workflow) - 1:
                print_info(f"Task {args.task_id} is already at final status: {current_status.value}")
                return
            target_status = workflow[current_idx + 1]

    # Check for override flag
    override = getattr(args, 'override', False)

    if override:
        # Display warning and log override
        print_warning(
            "⚠️  Using --override to bypass gate validation\n"
            "This should only be used in urgent situations.\n"
            "Override will be logged to data/kanban/info/override_log.txt"
        )
        reason = getattr(args, 'reason', None) or "No reason provided"
        log_override(storage, args.task_id, current_status.value, target_status.value, reason)
        # Move task with override action
        _move_task(storage, args.task_id, path, target_status, task, reason=reason, action="override_promote")
    else:
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

        # Move task normally
        _move_task(storage, args.task_id, path, target_status, task, action="promote")


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

    # Check for override flag
    override = getattr(args, 'override', False)

    if override:
        # Display warning and log override
        print_warning(
            "⚠️  Using --override to bypass gate validation\n"
            "This should only be used in urgent situations.\n"
            "Override will be logged to data/kanban/info/override_log.txt"
        )
        # Determine target first for logging
        workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                    TaskStatus.QA, TaskStatus.DONE]
        if hasattr(args, 'to') and args.to:
            target_status = TaskStatus(args.to)
        else:
            current_idx = workflow.index(current_status)
            if current_idx <= 0:
                print_info(f"Task {args.task_id} is already at initial status: {current_status.value}")
                return
            target_status = workflow[current_idx - 1]

        reason = getattr(args, 'reason', None) or "No reason provided"
        log_override(storage, args.task_id, current_status.value, target_status.value, reason)
    else:
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
        workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                    TaskStatus.QA, TaskStatus.DONE]

        if hasattr(args, 'to') and args.to:
            target_status = TaskStatus(args.to)
        else:
            # Special case: QA demotions go to REGRESSION (not back to ACTIVE)
            if current_status == TaskStatus.QA:
                target_status = TaskStatus.REGRESSION
                print_info(f"QA failure: moving {args.task_id} to regression status")
            # REGRESSION can go back to ACTIVE or promote to QA
            elif current_status == TaskStatus.REGRESSION:
                target_status = TaskStatus.ACTIVE
                print_info(f"Regression needs rework: moving {args.task_id} to active")
            else:
                # Normal workflow: previous in workflow
                current_idx = workflow.index(current_status)
                if current_idx <= 0:
                    print_info(f"Task {args.task_id} is already at initial status: {current_status.value}")
                    return
                target_status = workflow[current_idx - 1]

    # Move task with reason
    reason = getattr(args, 'reason', None)
    action = "override_demote" if override else "demote"
    _move_task(storage, args.task_id, path, target_status, task, reason=reason, action=action)


def cmd_move(args):
    """Move task(s) to specific status."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Require reason for move command
    if not hasattr(args, 'reason') or not args.reason:
        print_error("Move command requires --reason flag")
        print_info("Use 'taskpy promote' or 'taskpy demote' for workflow transitions")
        sys.exit(1)

    # Parse task IDs - support both space-separated and comma-delimited
    task_ids = parse_task_ids(args.task_ids)

    if not task_ids:
        print_error("No valid task IDs provided")
        sys.exit(1)

    target_status = TaskStatus(args.status)

    # Workflow order for detecting promotions/demotions
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                TaskStatus.QA, TaskStatus.DONE]

    # Track results
    successes = []
    failures = []

    # Process each task
    for task_id in task_ids:
        result = storage.find_task_file(task_id)
        if not result:
            failures.append((task_id, f"Task not found: {task_id}"))
            continue

        path, current_status = result

        # Warn if this looks like a workflow transition
        if current_status in workflow and target_status in workflow:
            current_idx = workflow.index(current_status)
            target_idx = workflow.index(target_status)
            if target_idx == current_idx + 1:
                print_warning(f"⚠️  {task_id}: Use 'taskpy promote' instead of 'move' for forward workflow transitions")
            elif target_idx == current_idx - 1:
                print_warning(f"⚠️  {task_id}: Use 'taskpy demote' instead of 'move' for backward workflow transitions")

        try:
            _move_task(storage, task_id, path, target_status, reason=args.reason, action="move")
            successes.append(task_id)
        except Exception as e:
            failures.append((task_id, str(e)))

    # Print summary if multiple tasks
    if len(task_ids) > 1:
        print()
        if successes:
            print_success(f"Successfully moved {len(successes)} of {len(task_ids)} tasks")
            for tid in successes:
                print(f"  ✓ {tid}")
        if failures:
            print()
            print_error(f"Failed to move {len(failures)} tasks:")
            for tid, error in failures:
                print(f"  ✗ {tid}: {error}")

    # Exit with error code if any failures
    if failures:
        sys.exit(1)


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
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
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
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(2)

    # Find task
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(2)

    path, current_status = result
    task = storage.read_task_file(path)

    # Check if task is blocked
    if task.status == TaskStatus.BLOCKED:
        reason = task.blocked_reason or "No reason provided"
        print_warning(f"Task {task.id} is blocked: {reason}")
        sys.exit(2)  # Blocked

    # Determine next status in workflow
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                TaskStatus.QA, TaskStatus.DONE]

    current_idx = workflow.index(current_status)
    if current_idx >= len(workflow) - 1:
        # Task is done
        print_success(f"Task {task.id} is already at final status ({current_status.value})")
        sys.exit(0)  # Ready (no more promotions)

    next_status = workflow[current_idx + 1]

    # Check gate requirements
    is_valid, blockers = validate_promotion(task, next_status, None)

    if is_valid:
        print_success(
            f"Ready: {task.id} can move {current_status.value} → {next_status.value}",
            "Stoplight"
        )
        sys.exit(0)
    else:
        print_warning(
            f"Missing requirements for {task.id}: {current_status.value} → {next_status.value}",
            "Stoplight"
        )
        for blocker in blockers:
            print(f"  • {blocker}")
        sys.exit(1)


def cmd_kanban(args):
    """Display kanban board."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Group tasks by status
    tasks_by_status = {}
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
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
    for status in [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
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
                task.verification.status = VerificationStatus.PASSED
                task.verification.last_run = utc_now()
                storage.write_task_file(task)
        else:
            print_error(f"Verification failed\n\nOutput:\n{result.stdout}\n{result.stderr}")
            if args.update:
                task.verification.status = VerificationStatus.FAILED
                task.verification.last_run = utc_now()
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


def _append_issue_to_task_file(task_path: Path, issue_description: str):
    """Append an issue to the task file's ISSUES section."""
    timestamp = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")
    issue_line = f"- **{timestamp}** - {issue_description}\n"

    # Read the file
    with open(task_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if ISSUES section exists (must be at start of line, not in code block)
    lines = content.split('\n')
    issues_idx = None
    in_code_block = False
    for i, line in enumerate(lines):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
        if line.strip() == "## ISSUES" and not in_code_block and not line.startswith((' ', '\t', '-', '*')):
            issues_idx = i
            break

    if issues_idx is not None:
        # Find next section or end of file
        next_section_idx = len(lines)
        for i in range(issues_idx + 1, len(lines)):
            if lines[i].startswith('## ') and lines[i].strip() != "## ISSUES":
                next_section_idx = i
                break

        # Insert before next section (or append if at end)
        lines.insert(next_section_idx, issue_line)
        content = '\n'.join(lines)
    else:
        # Add ISSUES section at the end
        if not content.endswith('\n'):
            content += '\n'
        content += f"\n## ISSUES\n\n{issue_line}"

    # Write back
    with open(task_path, 'w', encoding='utf-8') as f:
        f.write(content)


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
        if hasattr(args, 'verify') and args.verify:
            # Set verification command (use first one if multiple provided)
            task.verification.command = args.verify[0]
            # Reset verification status to pending when command changes
            task.verification.status = VerificationStatus.PENDING
        if hasattr(args, 'commit') and args.commit:
            # Set commit hash
            task.commit_hash = args.commit

        # Save task first (updates frontmatter and references)
        storage.write_task_file(task)

        # Handle issue annotations AFTER write (appends to markdown body)
        if hasattr(args, 'issue') and args.issue:
            for issue_desc in args.issue:
                _append_issue_to_task_file(path, issue_desc)

        print_success(f"References linked to {args.task_id}")

    except Exception as e:
        print_error(f"Failed to link references: {e}")
        sys.exit(1)


def cmd_issues(args):
    """Display issues/problems tracked for a task."""
    storage = get_storage()

    # Find task file
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result

    # Read file content to extract ISSUES section
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find ISSUES section
        lines = content.split('\n')
        issues_idx = None
        in_code_block = False

        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
            if line.strip() == "## ISSUES" and not in_code_block:
                issues_idx = i
                break

        if issues_idx is None:
            print_info(f"No issues tracked for {args.task_id}")
            return

        # Extract issues until next section or end
        issues = []
        for i in range(issues_idx + 1, len(lines)):
            line = lines[i]
            # Stop at next markdown section
            if line.startswith('## ') and line.strip() != "## ISSUES":
                break
            # Collect issue lines (bullets)
            if line.strip().startswith('- '):
                issues.append(line.strip())

        if not issues:
            print_info(f"No issues tracked for {args.task_id}")
            return

        # Display issues
        print_success(f"Issues for {args.task_id} ({len(issues)} found)")
        for issue in issues:
            print(f"  {issue}")

    except Exception as e:
        print_error(f"Failed to read issues: {e}")
        sys.exit(1)


def cmd_history(args):
    """Display task history and audit trail."""
    storage = get_storage()

    # Check if showing all tasks or single task
    if args.all:
        # Read all tasks from manifest
        rows = _read_manifest(storage)

        # Collect all tasks with history
        tasks_with_history = []
        for row in rows:
            task_id = row['id']
            result = storage.find_task_file(task_id)
            if result:
                path, _ = result
                try:
                    task = storage.read_task_file(path)
                    if task.history:
                        tasks_with_history.append(task)
                except Exception:
                    continue

        if not tasks_with_history:
            print_info("No tasks with history entries found")
            return

        # Display all history
        total_entries = sum(len(t.history) for t in tasks_with_history)
        print_success(f"History for {len(tasks_with_history)} tasks ({total_entries} total entries)", "All Task History")
        print()

        for task in tasks_with_history:
            print(f"[{task.id}] {task.title}")
            for entry in task.history:
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
                action = entry.action

                # Format based on action type
                if entry.from_status and entry.to_status:
                    transition = f"{entry.from_status} → {entry.to_status}"
                    action_display = f"{action}: {transition}"
                else:
                    action_display = action

                print(f"  [{timestamp}] {action_display}")
                if entry.reason:
                    print(f"    Reason: {entry.reason}")
                if entry.actor:
                    print(f"    Actor: {entry.actor}")
                if entry.metadata:
                    for key, value in entry.metadata.items():
                        print(f"    {key}: {value}")
            print()
        return

    # Single task mode
    if not args.task_id:
        print_error("Task ID required (or use --all to show all)")
        sys.exit(1)

    # Find task file
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result

    try:
        task = storage.read_task_file(path)

        if not task.history:
            print_info(f"No history entries for {args.task_id}")
            return

        # Display history in chronological order
        print_success(f"History for {args.task_id} ({len(task.history)} entries)", "Task History")
        print()

        for entry in task.history:
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            action = entry.action

            # Format based on action type
            if entry.from_status and entry.to_status:
                transition = f"{entry.from_status} → {entry.to_status}"
                action_display = f"{action}: {transition}"
            else:
                action_display = action

            print(f"  [{timestamp}] {action_display}")
            if entry.reason:
                print(f"    Reason: {entry.reason}")
            if entry.actor:
                print(f"    Actor: {entry.actor}")
            if entry.metadata:
                for key, value in entry.metadata.items():
                    print(f"    {key}: {value}")
            print()

    except Exception as e:
        print_error(f"Failed to read history: {e}")
        sys.exit(1)


def cmd_resolve(args):
    """
    Resolve a bug task with special resolution type.

    Only works for bug-like tasks (BUGS*, REG*, DEF*).
    Bypasses normal QA gates for non-fixed resolutions.
    """
    from taskpy.models import ResolutionType
    import re

    storage = get_storage()

    # Find task file
    result = storage.find_task_file(args.task_id)
    if not result:
        print_error(f"Task not found: {args.task_id}")
        sys.exit(1)

    path, current_status = result
    task = storage.read_task_file(path)

    # Validate task is bug-like
    if not re.match(r'^(BUGS|REG|DEF)', task.epic):
        print_error(f"Resolve command only works for bug-like tasks (BUGS*, REG*, DEF*)")
        print_error(f"Task {args.task_id} has epic: {task.epic}")
        print_error(f"Use normal promote workflow for feature tasks")
        sys.exit(1)

    # Convert resolution string to enum
    resolution = ResolutionType(args.resolution)

    # Validate duplicate_of is provided for duplicate resolutions
    if resolution == ResolutionType.DUPLICATE and not args.duplicate_of:
        print_error("--duplicate-of is required when resolution is 'duplicate'")
        sys.exit(1)

    # Set resolution metadata
    task.resolution = resolution
    task.resolution_reason = args.reason
    if args.duplicate_of:
        task.duplicate_of = args.duplicate_of

    # Move to done
    old_status = task.status
    task.status = TaskStatus.DONE
    task.updated = utc_now()

    # Save task
    try:
        # Delete old file if status changed
        if old_status != TaskStatus.DONE:
            path.unlink()

        storage.write_task_file(task)

        # Display resolution
        print_success(f"Resolved {args.task_id}: {old_status.value} → done")
        print_info(f"Resolution: {resolution.value}")
        print_info(f"Reason: {args.reason}")
        if args.duplicate_of:
            print_info(f"Duplicate of: {args.duplicate_of}")

        # Note about bypassed gates
        if resolution != ResolutionType.FIXED:
            print_warning("⚠️  Bypassed normal QA gates (non-code resolution)")

    except Exception as e:
        print_error(f"Failed to resolve task: {e}")
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
  taskpy block TASK-ID --reason REASON  Block with required reason
  taskpy unblock TASK-ID                Return blocked task to backlog
  taskpy groom                          Audit stub/backlog detail depth
  taskpy stoplight TASK-ID              Gate check (0=ready, 1=missing, 2=blocked)

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
  taskpy overrides                           View override history

DATA MAINTENANCE
----------------
  taskpy manifest rebuild                 Resync manifest.tsv
  taskpy groom                            Audit stub/backlog detail depth

WORKFLOW STATUSES
-----------------
  stub → backlog → ready → active → qa → done → archived

  stub         Incomplete, needs grooming
  backlog      Groomed, ready for work
  ready        Selected for sprint
  active  Actively being developed
  qa           In testing/review
  done         Completed
  archived     Long-term storage
  blocked      Blocked by dependencies (special state)

USEFUL FLAGS
------------
  --agent                               Agent-friendly output (no boxy formatting)
  --view=data                           Plain output (same as --agent)
  --no-boxy                             Same as --agent
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
    task.updated = utc_now()
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
    task.updated = utc_now()
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

    # Display tasks as table (include Sprint column for consistency)
    headers = ["ID", "Epic", "#", "Title", "Status", "SP", "Priority", "Sprint"]
    table_rows = [_manifest_row_to_table(task) for task in sprint_tasks]
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
            task.updated = utc_now()
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
    for status in ['stub', 'backlog', 'ready', 'active', 'qa', 'regression', 'done', 'blocked']:
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


def cmd_overrides(args):
    """View override usage history."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    log_file = storage.info_dir / "override_log.txt"

    if not log_file.exists():
        print_info("No overrides logged yet")
        print(f"Override log: {log_file}")
        return

    # Read and display log
    with open(log_file, "r") as f:
        lines = f.readlines()

    if not lines:
        print_info("No overrides logged yet")
        return

    print(f"\n{'='*80}")
    print(f"Override History ({len(lines)} total)")
    print(f"{'='*80}\n")

    # Show most recent entries (default: all, could add --limit later)
    for line in reversed(lines):
        print(line.rstrip())

    print()


def cmd_block(args):
    """Block a task with required reason."""
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

    # Check if already blocked
    if task.status == TaskStatus.BLOCKED:
        print_info(f"Task {args.task_id} is already blocked")
        print(f"Reason: {task.blocked_reason or '(no reason provided)'}")
        return

    # Store previous status and set blocked
    task.blocked_reason = args.reason

    # Move to blocked status
    _move_task(storage, args.task_id, path, TaskStatus.BLOCKED, task, reason=args.reason, action="block")

    print_info(f"Reason: {args.reason}")


def cmd_unblock(args):
    """Unblock a task and return to previous status."""
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

    # Check if blocked
    if task.status != TaskStatus.BLOCKED:
        print_info(f"Task {args.task_id} is not blocked (status: {task.status.value})")
        return

    # Determine target status - default to backlog if can't determine
    # In a more sophisticated implementation, we'd store previous_status
    # For now, use backlog as safe default
    target_status = TaskStatus.BACKLOG

    # Clear blocked reason
    task.blocked_reason = None

    # Move back to target status
    _move_task(storage, args.task_id, path, target_status, task, action="unblock")

    print_info(f"Task {args.task_id} unblocked and moved to {target_status.value}")


# Helper functions

def _open_in_editor(path: Path):
    """Open file in $EDITOR."""
    editor = os.environ.get('EDITOR', 'vi')
    subprocess.run([editor, str(path)])


def _move_task(storage: TaskStorage, task_id: str, current_path: Path, target_status: TaskStatus, task: Optional[Task] = None, reason: Optional[str] = None, action: str = "move"):
    """Move a task to a new status and log to history."""
    try:
        # Read task if not provided
        if task is None:
            task = storage.read_task_file(current_path)

        # Update status
        old_status = task.status
        task.status = target_status

        # Add history entry
        from taskpy.models import HistoryEntry, utc_now
        history_entry = HistoryEntry(
            timestamp=utc_now(),
            action=action,
            from_status=old_status.value,
            to_status=target_status.value,
            reason=reason
        )
        task.history.append(history_entry)

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



def _format_task_number(number_value: Optional[str]) -> str:
    """Format manifest number column similar to Task IDs."""
    if not number_value:
        return "-"
    try:
        number = int(number_value)
    except (TypeError, ValueError):
        return str(number_value)

    if number < 10:
        return f"0{number}"
    if number < 100:
        return f"{number:02d}"
    return str(number)


def _format_title_column(title: Optional[str]) -> str:
    """Return clean title string without manual truncation."""
    if not title:
        return ""
    return title.strip()


def _manifest_row_to_table(row: Dict[str, str]) -> List[str]:
    """Convert manifest row dict to table row for display."""
    # Sprint indicator: checkmark for sprint tasks, empty for others
    sprint_indicator = '✓' if row.get('in_sprint', 'false') == 'true' else ''

    return [
        row.get('id', ''),
        row.get('epic', ''),
        _format_task_number(row.get('number')),
        _format_title_column(row.get('title')),
        row.get('status', ''),
        row.get('story_points', '0'),
        row.get('priority', ''),
        sprint_indicator,
    ]


def _read_manifest(storage: TaskStorage):
    """Read all rows from manifest."""
    import csv

    def _load_rows() -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        if not storage.manifest_file.exists():
            storage._create_manifest_header()
        with open(storage.manifest_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                rows.append(row)
        return rows

    rows = _load_rows()
    if not rows:
        rebuilt = storage.rebuild_manifest()
        if rebuilt > 0:
            rows = _load_rows()
    return rows


def _read_manifest_with_filters(storage: TaskStorage, args):
    """Read manifest and apply filters."""
    rows = _read_manifest(storage)

    # Hide done/archived by default unless --all or --status=done/archived explicitly requested
    if hasattr(args, 'all'):
        explicit_status_filter = hasattr(args, 'status') and args.status and args.status in ['done', 'archived']
        if not args.all and not explicit_status_filter:
            rows = [r for r in rows if r['status'] not in ['done', 'archived']]

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


def _collect_status_tasks(storage: TaskStorage, statuses: Iterable[TaskStatus]) -> List[Tuple[Task, int]]:
    """Collect Task objects and their content lengths for given statuses."""
    tasks: List[Tuple[Task, int]] = []
    for status in statuses:
        dir_path = storage.status_dir / status.value
        if not dir_path.exists():
            continue
        for path in sorted(dir_path.glob('*.md')):
            try:
                content = path.read_text()
            except OSError as exc:
                print_warning(f"Unable to read {path}: {exc}")
                continue
            length = len(content)
            try:
                task = storage.read_task_file(path)
            except Exception as exc:
                print_warning(f"Unable to parse {path}: {exc}")
                continue
            tasks.append((task, length))
    return tasks


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


def cmd_manifest(args):
    """Manage manifest operations."""
    if not args.manifest_command:
        print_error("Please specify a manifest subcommand: rebuild")
        sys.exit(1)

    handlers = {
        'rebuild': _cmd_manifest_rebuild,
    }

    handler = handlers.get(args.manifest_command)
    if handler is None:
        print_error(f"Unknown manifest subcommand: {args.manifest_command}")
        sys.exit(1)
    handler(args)


def _cmd_manifest_rebuild(args):
    """Rebuild manifest.tsv from task files."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    count = storage.rebuild_manifest()

    if count == 0:
        print_warning(
            "No task files found while rebuilding manifest.\n"
            "Create tasks with `taskpy create` first.",
            "Manifest Rebuild"
        )
    else:
        print_success(
            f"Indexed {count} tasks into manifest.tsv\n"
            f"Path: {storage.manifest_file}",
            "Manifest Rebuilt"
        )


def cmd_groom(args):
    """Audit stub tasks for sufficient detail."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    done_tasks = _collect_status_tasks(storage, [TaskStatus.DONE, TaskStatus.ARCHIVED])
    done_lengths = [length for _, length in done_tasks]

    if done_lengths:
        done_median = statistics.median(done_lengths)
        threshold = max(int(done_median * args.ratio), args.min_chars)
    else:
        done_median = None
        fallback_done = 1000
        threshold = max(int(fallback_done * args.ratio), args.min_chars, 500)

    stub_tasks = _collect_status_tasks(storage, [TaskStatus.STUB])
    stub_lengths = [length for _, length in stub_tasks]

    print_info(
        (
            f"Stub tasks audited: {len(stub_tasks)}\n"
            f"Done median: {done_median:.0f} chars\n" if done_median else "No done tasks found, using fallback median (1000 chars).\n"
        ) + f"Detail threshold: {threshold} chars",
        "Groom Summary"
    )

    short_tasks = []
    if not stub_tasks:
        print_success("No stub tasks found", "Groom Check")
    else:
        short_tasks = [
            (task, length, threshold - length)
            for task, length in stub_tasks
            if length < threshold
        ]

        if not short_tasks:
            print_success(
                f"All stub tasks meet the minimum detail threshold ({threshold} chars)",
                "Groom Check"
            )
        else:
            headers = ["ID", "Chars", "Short By", "Title"]
            rows = [
                [
                    t.id,
                    length,
                    deficit,
                    t.title[:80]
                ]
                for t, length, deficit in short_tasks
            ]
            rolo_table(headers, rows, "Stub tasks needing more detail")

            if args.override:
                print_info(
                    "Override acknowledged. No warnings emitted, but please review the tasks above to confirm they are intentionally brief.",
                    "Groom Override"
                )
            else:
                print_warning(
                    "These stub tasks look under-specified. Review Description/Acceptance Criteria/Notes and flesh them out if the brevity was unintentional.",
                    "Groom Review Required"
                )

    backlog_tasks = _collect_status_tasks(storage, [TaskStatus.BACKLOG])
    backlog_short = [
        (task, length, threshold - length)
        for task, length in backlog_tasks
        if length < threshold
    ]

    if backlog_short:
        headers = ["ID", "Chars", "Short By", "Title"]
        rows = [
            [
                t.id,
                length,
                deficit,
                t.title[:80]
            ]
            for t, length, deficit in backlog_short
        ]
        rolo_table(headers, rows, "Backlog tasks needing more detail")

        if args.override:
            print_info(
                "Override acknowledged for backlog items. No warnings emitted, but double-check these tickets before sprinting.",
                "Backlog Groom Override"
            )
        else:
            print_warning(
                "Backlog tasks above look under-specified. Review and add details before sprinting.",
                "Backlog Groom Review Required"
            )


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
