"""Create operations for core task management."""

import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error, print_success, print_warning
from taskpy.legacy.commands import _open_in_editor, validate_promotion
from taskpy.legacy.models import Task, TaskStatus, Priority


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


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
        content=content,
        auto_id=storage.get_next_auto_id()  # Assign global sequence ID
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


__all__ = ['cmd_create']
