"""Command implementations for core task management."""

import re
import sys
from pathlib import Path

from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_error, print_info, print_success, print_warning, get_output_mode, OutputMode, display_task_card
from taskpy.legacy.commands import _read_manifest, _sort_tasks, _format_title_column, parse_task_ids, validate_promotion, _open_in_editor
from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.utils import utc_now
from taskpy.modern.views import ListView, ColumnConfig


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


def _read_manifest_with_filters(storage: TaskStorage, args):
    """Read manifest and apply filters."""
    rows = _read_manifest(storage)

    # Hide done/archived by default unless --all or --status=done/archived explicitly requested
    explicit_status_filter = hasattr(args, 'status') and args.status and args.status in ['done', 'archived']
    show_all = hasattr(args, 'all') and args.all
    if not show_all and not explicit_status_filter:
        rows = [r for r in rows if r['status'] not in ['done', 'archived']]

    # Apply filters
    if hasattr(args, 'epic') and args.epic:
        rows = [r for r in rows if r['epic'] == args.epic.upper()]

    if hasattr(args, 'status') and args.status:
        rows = [r for r in rows if r['status'] == args.status]

    if hasattr(args, 'priority') and args.priority:
        rows = [r for r in rows if r['priority'] == args.priority]

    if hasattr(args, 'milestone') and args.milestone:
        rows = [r for r in rows if r.get('milestone') == args.milestone]

    if hasattr(args, 'sprint') and args.sprint:
        sprint_value = 'true' if args.sprint else 'false'
        rows = [r for r in rows if r.get('in_sprint', 'false') == sprint_value]

    return rows


def cmd_list(args):
    """List tasks with optional filters using modern ListView."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Read manifest and apply filters
    tasks = _read_manifest_with_filters(storage, args)

    if not tasks:
        print_info("No tasks found matching filters")
        return

    # Apply sorting
    sort_mode = getattr(args, 'sort', 'priority')
    tasks = _sort_tasks(tasks, sort_mode)

    # Configure columns
    columns = [
        ColumnConfig(name="ID", field="id"),
        ColumnConfig(name="Title", field=lambda t: _format_title_column(t.get('title'))),
        ColumnConfig(name="Status", field="status"),
        ColumnConfig(name="SP", field="story_points"),
        ColumnConfig(name="Priority", field="priority"),
        ColumnConfig(name="Sprint", field=lambda t: '✓' if t.get('in_sprint', 'false') == 'true' else ''),
    ]

    # Create and render ListView
    view = ListView(
        data=tasks,
        columns=columns,
        title=f"Tasks ({len(tasks)} found)",
        output_mode=get_output_mode(),
        status_field='status',
        grey_done=True,
    )
    view.render()


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

        # Add references if present
        if task.references.code or task.references.docs:
            references_list = []
            if task.references.code:
                references_list.append(f"Code: {', '.join(task.references.code)}")
            if task.references.docs:
                references_list.append(f"Docs: {', '.join(task.references.docs)}")
            task_dict['references'] = '\n'.join(references_list)

        display_task_card(task_dict)

        # Show metadata if in data mode
        if get_output_mode() == OutputMode.DATA:
            print(f"\nCreated: {task.created.isoformat()}")
            print(f"Updated: {task.updated.isoformat()}")
            if task.nfrs:
                print(f"NFRs: {', '.join(task.nfrs)}")
            if task.references.code:
                print(f"Code: {', '.join(task.references.code)}")
            if task.references.docs:
                print(f"Docs: {', '.join(task.references.docs)}")
            if task.verification.command:
                print(f"Verification: {task.verification.command}")
                print(f"Status: {task.verification.status.value}")
            if task.resolution:
                print(f"\nResolution: {task.resolution.value}")
                print(f"Reason: {task.resolution_reason}")
                if task.duplicate_of:
                    print(f"Duplicate of: {task.duplicate_of}")


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


def cmd_rename(args):
    """
    Rename a task's ID (epic and/or number).
    Updates frontmatter, content, filename, and optionally manifest.
    """
    storage = get_storage()

    # Parse old and new IDs
    try:
        old_epic, old_number = Task.parse_task_id(args.old_id)
        new_epic, new_number = Task.parse_task_id(args.new_id)
    except ValueError as e:
        print_error(f"Invalid task ID format: {e}")
        sys.exit(1)

    # Find old task
    result = storage.find_task_file(args.old_id)
    if not result:
        print_error(f"Task not found: {args.old_id}")
        sys.exit(1)

    old_path, current_status = result

    # Check if new ID already exists (unless force)
    if not args.force:
        new_result = storage.find_task_file(args.new_id)
        if new_result:
            print_error(f"Task {args.new_id} already exists")
            print_info("Use --force to overwrite")
            sys.exit(1)

    # Read task
    task = storage.read_task_file(old_path)

    # Update task fields
    task.id = args.new_id
    task.epic = new_epic
    task.number = new_number
    task.updated = utc_now()

    # Read the markdown content to update ID references
    with open(old_path, 'r') as f:
        content = f.read()

    # Replace old ID with new ID in content (using word boundaries for safety)
    # Match the old ID but not as part of a longer word
    pattern = r'\b' + re.escape(args.old_id) + r'\b'
    updated_content = re.sub(pattern, args.new_id, content)

    # Write task to new location
    new_path = storage.status_dir / current_status.value / f"{args.new_id}.md"

    # Write the updated content directly (includes frontmatter changes from task object)
    storage.write_task_file(task)

    # If we need to update content beyond what write_task_file does
    # Re-read and update content sections
    with open(new_path, 'r') as f:
        final_content = f.read()

    # Replace ID in the body (after frontmatter)
    parts = final_content.split('---\n', 2)
    if len(parts) == 3:
        frontmatter_start, frontmatter_body, markdown_body = parts
        # Update markdown body
        pattern = r'\b' + re.escape(args.old_id) + r'\b'
        updated_body = re.sub(pattern, args.new_id, markdown_body)
        final_content = f"---\n{frontmatter_body}---\n{updated_body}"

        with open(new_path, 'w') as f:
            f.write(final_content)

    # Delete old file
    old_path.unlink()

    # Update manifest (unless skip flag)
    if not args.skip_manifest:
        # Rebuild manifest to pick up the rename
        storage.rebuild_manifest()

    print_success(f"Renamed {args.old_id} → {args.new_id}")
    if current_status != TaskStatus.STUB:
        print_info(f"File moved: {current_status.value}/{args.new_id}.md")


__all__ = ['cmd_list', 'cmd_show', 'cmd_create', 'cmd_edit', 'cmd_rename']
