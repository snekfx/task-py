"""Command implementations for workflow features.

This module provides task workflow management commands:
- promote: Move task forward in workflow
- demote: Move task backward in workflow
- move: Move task to specific status
- resolve: Resolve bug tasks with special outcomes

Migrated from legacy/commands.py (lines 583-810, 1345-1418, 2080-2115)
"""

import re
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from taskpy.legacy.models import Task, TaskStatus, HistoryEntry, utc_now, VerificationStatus, ResolutionType
from taskpy.legacy.storage import TaskStorage
from taskpy.legacy.output import print_success, print_error, print_info, print_warning
from taskpy.modern.shared.config import (
    is_feature_enabled,
    load_signoff_list,
    remove_signoff_tickets,
)
from taskpy.modern.shared.utils import load_task_or_exit, require_initialized

STRICT_FLAG_NAME = "strict_mode"
SIGNOFF_FLAG_NAME = "signoff_mode"


class TaskMoveError(Exception):
    """Raised when a workflow move operation fails."""


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


# =============================================================================
# Helper Functions
# =============================================================================

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


def _assert_not_strict_override():
    """Exit if strict mode blocks override/forced workflow changes."""
    if is_feature_enabled(STRICT_FLAG_NAME):
        print_error(
            "Strict mode is enabled: workflow overrides are blocked.\n"
            "Disable strict_mode via `taskpy flag disable strict_mode` to proceed."
        )
        sys.exit(1)


def _archive_from_promote(storage: TaskStorage, task: Task, path: Path, reason: Optional[str], signoff: bool):
    """Archive a done task with signoff gating."""
    if not signoff:
        print_error("Archiving done tasks requires --signoff. Add to signoff list with `taskpy signoff add TASK-ID`.")
        sys.exit(1)

    signoff_mode = is_feature_enabled(SIGNOFF_FLAG_NAME, storage.root)
    signoff_list = set(load_signoff_list(storage.root))

    if signoff_mode and task.id not in signoff_list:
        print_error(
            f"{task.id} is not in the signoff list (signoff_mode enabled).\n"
            "Add it via: taskpy signoff add {task.id}"
        )
        sys.exit(1)

    if not signoff_mode and task.id not in signoff_list and not (reason and reason.strip()):
        print_error(
            f"{task.id} not signed off. Provide --reason to document the archive, or add to signoff list.\n"
            "Examples:\n"
            f"  taskpy signoff add {task.id}\n"
            f"  taskpy promote {task.id} --signoff --reason \"manager approval\""
        )
        sys.exit(1)

    task.status = TaskStatus.ARCHIVED
    metadata = {
        "signoff_mode": signoff_mode,
        "signoff_listed": task.id in signoff_list,
    }
    if reason:
        metadata["reason"] = reason

    history_entry = HistoryEntry(
        timestamp=utc_now(),
        action="archive",
        from_status=TaskStatus.DONE.value,
        to_status=TaskStatus.ARCHIVED.value,
        reason=reason or None,
        metadata=metadata,
    )
    task.history.append(history_entry)

    try:
        path.unlink()
    except FileNotFoundError:
        pass
    storage.write_task_file(task)

    if task.id in signoff_list:
        remove_signoff_tickets([task.id], storage.root)
    print_success(f"Archived {task.id}", "Task Archived")


def log_override(storage: TaskStorage, task_id: str, from_status: str, to_status: str, reason: Optional[str] = None) -> Optional[Task]:
    """
    Log override event to task history.

    Creates a HistoryEntry with action='override' and appends it to the task's history.
    NOTE: This does NOT save the task - the caller should save it after making other changes.

    Args:
        storage: TaskStorage instance
        task_id: Task ID being overridden
        from_status: Status being transitioned from
        to_status: Status being transitioned to
        reason: Optional reason for the override

    Returns:
        Updated Task object with override history entry, or None if task not found
    """
    # Find and load the task
    result = storage.find_task_file(task_id)
    if not result:
        print_warning(f"Could not log override for {task_id}: task not found")
        return None

    task_path, _ = result
    task = storage.read_task_file(task_path)

    # Add override entry to task history
    history_entry = HistoryEntry(
        timestamp=utc_now(),
        action='override',
        from_status=from_status,
        to_status=to_status,
        reason=reason
    )
    task.history.append(history_entry)

    return task


def _move_task(storage: TaskStorage, task_id: str, current_path: Path, target_status: TaskStatus,
               task: Optional[Task] = None, reason: Optional[str] = None, action: str = "move"):
    """Move a task to a new status and log to history."""
    try:
        if task is None:
            task = storage.read_task_file(current_path)

        old_status = task.status
        task.status = target_status

        history_entry = HistoryEntry(
            timestamp=utc_now(),
            action=action,
            from_status=old_status.value,
            to_status=target_status.value,
            reason=reason
        )
        task.history.append(history_entry)

        current_path.unlink()
        storage.write_task_file(task)

        print_success(
            f"Moved {task_id}: {old_status.value} → {target_status.value}",
            "Task Moved"
        )

    except Exception as exc:
        raise TaskMoveError(f"{task_id}: {exc}") from exc


# =============================================================================
# Gate Validation Functions
# =============================================================================

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
        return validate_active_to_qa(task)  # Same requirements as active→qa

    # qa → done
    elif current == TaskStatus.QA and target_status == TaskStatus.DONE:
        # Allow commit_hash to be provided as argument
        if commit_hash:
            task.commit_hash = commit_hash
        return validate_qa_to_done(task)

    # No specific validation for other transitions
    return (True, [])


# =============================================================================
# Workflow Commands
# =============================================================================

def cmd_promote(args):
    """Move task forward in workflow."""
    storage = get_storage()
    require_initialized(storage)
    task, path, current_status = load_task_or_exit(storage, args.task_id)

    # Archival path: promoting done -> archived
    if current_status == TaskStatus.DONE:
        reason = getattr(args, "reason", None)
        _archive_from_promote(storage, task, path, reason, getattr(args, "signoff", False))
        return

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
        _assert_not_strict_override()
        # Display warning and log override
        print_warning(
            "⚠️  Using --override to bypass gate validation\n"
            "This should only be used in urgent situations.\n"
            "Override will be logged to task history"
        )
        reason = getattr(args, 'reason', None) or "No reason provided"

        # Log override to history and get updated task
        task = log_override(storage, args.task_id, current_status.value, target_status.value, reason)
        if not task:
            return

        # Now move the task (this will add a separate promote entry to history)
        _move_task(storage, args.task_id, path, target_status, task, reason=reason, action="promote")
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
    require_initialized(storage)
    task, path, current_status = load_task_or_exit(storage, args.task_id)

    # Check for override flag
    override = getattr(args, 'override', False)

    if override:
        _assert_not_strict_override()
        # Display warning and log override
        print_warning(
            "⚠️  Using --override to bypass gate validation\n"
            "This should only be used in urgent situations.\n"
            "Override will be logged to task history"
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
        task = log_override(storage, args.task_id, current_status.value, target_status.value, reason)
        if not task:
            return
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
            # Special cases
            if current_status == TaskStatus.QA:
                # QA demotions go to REGRESSION (not back to ACTIVE)
                target_status = TaskStatus.REGRESSION
                print_info(f"QA failure: moving {args.task_id} to regression status")
            elif current_status == TaskStatus.DONE:
                # Done demotions go to regression for rework
                target_status = TaskStatus.REGRESSION
                print_info(f"Demoting {args.task_id} from done to regression status")
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

    # Move task with reason (action is always "demote" since override is logged separately)
    reason = getattr(args, 'reason', None)
    _move_task(storage, args.task_id, path, target_status, task, reason=reason, action="demote")


def cmd_move(args):
    """Move task(s) to specific status."""
    storage = get_storage()
    require_initialized(storage)

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

    if is_feature_enabled(STRICT_FLAG_NAME) and target_status in {TaskStatus.QA, TaskStatus.DONE}:
        print_error(
            "Strict mode blocks moving tasks directly to QA or done.\n"
            "Use workflow promotions or disable strict_mode via `taskpy flag disable strict_mode`."
        )
        sys.exit(1)

    # Workflow order for detecting promotions/demotions
    workflow = [TaskStatus.STUB, TaskStatus.BACKLOG, TaskStatus.READY, TaskStatus.ACTIVE,
                TaskStatus.QA, TaskStatus.DONE]

    # Track results
    successes = []
    failures = []

    # Process each task
    for task_id in task_ids:
        try:
            task, path, current_status = load_task_or_exit(storage, task_id)
        except SystemExit:
            failures.append((task_id, f"Task not found: {task_id}"))
            continue

        # Warn if this looks like a workflow transition
        if current_status in workflow and target_status in workflow:
            current_idx = workflow.index(current_status)
            target_idx = workflow.index(target_status)
            if target_idx == current_idx + 1:
                print_warning(f"⚠️  {task_id}: Use 'taskpy promote' instead of 'move' for forward workflow transitions")
            elif target_idx == current_idx - 1:
                print_warning(f"⚠️  {task_id}: Use 'taskpy demote' instead of 'move' for backward workflow transitions")

        try:
            _move_task(storage, task_id, path, target_status, task, reason=args.reason, action="move")
            successes.append(task_id)
        except TaskMoveError as exc:
            failures.append((task_id, str(exc)))
        except Exception as exc:  # pragma: no cover - unexpected failures
            failures.append((task_id, str(exc)))

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


def cmd_resolve(args):
    """Resolve bug tasks with special resolution types."""
    storage = get_storage()
    require_initialized(storage)

    task, path, _ = load_task_or_exit(storage, args.task_id)

    if not re.match(r'^(BUGS|REG|DEF)', task.epic):
        print_error("Resolve command only works for BUGS*/REG*/DEF* tasks")
        print_error(f"Task {args.task_id} has epic: {task.epic}")
        print_error("Use normal promote workflow for other epics")
        sys.exit(1)

    resolution = ResolutionType(args.resolution)
    if resolution == ResolutionType.DUPLICATE and not args.duplicate_of:
        print_error("--duplicate-of is required when resolution is 'duplicate'")
        sys.exit(1)

    task.resolution = resolution
    task.resolution_reason = args.reason
    if args.duplicate_of:
        task.duplicate_of = args.duplicate_of

    old_status = task.status
    task.status = TaskStatus.DONE
    task.updated = utc_now()

    try:
        if old_status != TaskStatus.DONE:
            path.unlink()
        storage.write_task_file(task)

        print_success(f"Resolved {args.task_id}: {old_status.value} → done")
        print_info(f"Resolution: {resolution.value}")
        print_info(f"Reason: {args.reason}")
        if args.duplicate_of:
            print_info(f"Duplicate of: {args.duplicate_of}")
        if resolution != ResolutionType.FIXED:
            print_warning("⚠️  Bypassed normal QA gates (non-code resolution)")
    except Exception as exc:
        print_error(f"Failed to resolve task: {exc}")
        sys.exit(1)


__all__ = ['cmd_promote', 'cmd_demote', 'cmd_move', 'cmd_resolve']
