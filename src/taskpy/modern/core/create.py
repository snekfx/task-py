"""Create operations for core task management."""

import sys
from pathlib import Path

from taskpy.modern.shared.messages import print_error, print_success, print_warning
from taskpy.modern.shared.tasks import (
    KanbanNotInitialized,
    TaskRecord,
    ensure_initialized,
    load_epics,
    load_milestones,
    load_nfrs,
    make_task_id,
    next_task_number,
    next_auto_id,
    write_task,
    get_task_path,
    open_in_editor,
    find_task_file,
)


def cmd_create(args):
    """Create a new task."""
    try:
        ensure_initialized(Path.cwd())
    except KanbanNotInitialized:
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    epics = load_epics()

    raw_epic = args.epic.strip().upper()
    manual_number = None

    if "-" in raw_epic:
        epic_name, number_str = raw_epic.split("-", 1)
        if not number_str.isdigit():
            print_error("Manual IDs must use format EPIC-123 (digits only).")
            sys.exit(1)
        manual_number = int(number_str)
        if manual_number <= 0 or manual_number > 999:
            print_error("Manual task numbers must be between 1 and 999.")
            sys.exit(1)
    else:
        epic_name = raw_epic

    if epic_name not in epics:
        print_error(
            f"Unknown epic: {epic_name}\n"
            f"Available epics: {', '.join(epics.keys())}\n"
            f"Add new epic in: data/kanban/info/epics.toml"
        )
        sys.exit(1)

    if not epics[epic_name].get("active", True):
        print_warning(f"Epic {epic_name} is marked inactive")

    auto_bump = getattr(args, "auto", False)

    if manual_number is not None:
        number = manual_number
    else:
        number = next_task_number(epic_name)

    task_id = make_task_id(epic_name, number)

    if manual_number is not None:
        existing = find_task_file(task_id)
        if existing:
            if auto_bump:
                original_number = number
                while existing:
                    number += 1
                    if number > 999:
                        print_error("No available IDs remaining in this epic (limit 999).")
                        sys.exit(1)
                    task_id = make_task_id(epic_name, number)
                    existing = find_task_file(task_id)
                print_warning(
                    f"{make_task_id(epic_name, original_number)} already exists. "
                    f"Using next available ID: {task_id}",
                    "Auto ID Adjustment"
                )
            else:
                print_error(
                    f"Task ID {task_id} already exists. Use --auto to select the next "
                    "available number automatically."
                )
                sys.exit(1)

    # Parse title
    title = " ".join(args.title)

    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',')]

    # Validate milestone if provided
    milestone = None
    if getattr(args, "milestone", None):
        milestones = load_milestones()
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

    priority = args.priority.lower()
    if priority not in {"critical", "high", "medium", "low"}:
        print_error("Invalid priority. Use one of: critical, high, medium, low.")
        sys.exit(1)

    status = args.status.lower()
    if status not in {"stub", "backlog", "ready", "active", "qa", "blocked"}:
        print_error(
            "Invalid status. Use one of: stub, backlog, ready, active, qa, blocked."
        )
        sys.exit(1)

    task = TaskRecord(
        id=task_id,
        title=title,
        epic=epic_name,
        number=number,
        status=status,
        story_points=args.story_points,
        priority=priority,
        tags=tags,
        milestone=milestone,
        content=content,
        auto_id=next_auto_id(),
    )

    nfrs = load_nfrs()
    default_nfrs = [
        nfr_id for nfr_id, nfr in nfrs.items() if bool(nfr.get("default"))
    ]
    task.nfrs = default_nfrs

    try:
        write_task(task)
        task_path = get_task_path(task.id, task.status)
        milestone_info = f"Milestone: {milestone}\n" if milestone else ""

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
            f"{grooming_msg}\n"
            f"View: taskpy show {task_id}\n"
            f"Edit: taskpy edit {task_id}",
            f"Task {task_id} Created"
        )

        # Open in editor if requested
        if args.edit:
            open_in_editor(task_path)
    except Exception as e:
        print_error(f"Failed to create task: {e}")
        sys.exit(1)


__all__ = ['cmd_create']
