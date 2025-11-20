"""Command implementations for admin/maintenance features.

This module provides administrative and maintenance commands:
- init: Initialize TaskPy kanban structure
- verify: Run verification tests for tasks
- manifest: Manage manifest operations (rebuild)
- groom: Audit stub tasks for sufficient detail
- session: Manage work sessions

Migrated from legacy/commands.py (lines 220-259, 936-995, 1389-1393, 2347-2420)
"""

import json
import sys
import subprocess
import statistics
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Iterable, Dict, Any, Optional
from taskpy.legacy.models import Task, TaskStatus, VerificationStatus, utc_now
from taskpy.legacy.storage import TaskStorage, StorageError
from taskpy.legacy.output import print_success, print_error, print_info, print_warning


def get_storage() -> TaskStorage:
    """Get TaskStorage for current directory."""
    return TaskStorage(Path.cwd())


SESSION_STATE_FILENAME = "session_current.json"
SESSION_LOG_FILENAME = "sessions.jsonl"
SESSION_SEQUENCE_FILENAME = ".session_seq"


def _session_paths(storage: TaskStorage) -> tuple[Path, Path, Path]:
    """Return (state_path, log_path, sequence_path) under kanban/info."""
    info_dir = storage.kanban / "info"
    info_dir.mkdir(parents=True, exist_ok=True)
    state_path = info_dir / SESSION_STATE_FILENAME
    log_path = info_dir / SESSION_LOG_FILENAME
    sequence_path = info_dir / SESSION_SEQUENCE_FILENAME
    return state_path, log_path, sequence_path


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print_warning(f"Session file {path} is corrupted; ignoring.")
        return None


def _write_json(path: Path, data: Dict[str, Any]):
    path.write_text(json.dumps(data, indent=2))


def _append_session_log(path: Path, session: Dict[str, Any]):
    line = json.dumps(session)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _next_session_id(sequence_path: Path) -> str:
    if sequence_path.exists():
        try:
            current = int(sequence_path.read_text().strip())
        except ValueError:
            current = 0
    else:
        current = 0
    next_value = current + 1
    sequence_path.write_text(str(next_value))
    return f"session-{next_value:03d}"


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0m"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{sec}s"


# =============================================================================
# Helper Functions
# =============================================================================

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


# =============================================================================
# Admin Commands
# =============================================================================

def cmd_init(args):
    """Initialize TaskPy kanban structure."""
    storage = get_storage()

    try:
        # Get explicit type from args if provided
        project_type = getattr(args, 'type', None)

        # Initialize with project type detection
        detected_type, auto_detected = storage.initialize(
            force=getattr(args, 'force', False),
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

        update = getattr(args, 'update', False)
        if result.returncode == 0:
            print_success("Verification passed")
            if update:
                task.verification.status = VerificationStatus.PASSED
                task.verification.last_run = utc_now()
                storage.write_task_file(task)
        else:
            print_error(f"Verification failed\n\nOutput:\n{result.stdout}\n{result.stderr}")
            if update:
                task.verification.status = VerificationStatus.FAILED
                task.verification.last_run = utc_now()
                task.verification.output = result.stderr
                storage.write_task_file(task)
            sys.exit(1)

    except subprocess.TimeoutExpired:
        print_error("Verification command timed out (300s)")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error running verification: {e}")
        sys.exit(1)


def cmd_manifest(args):
    """Manage manifest operations."""
    manifest_command = getattr(args, 'manifest_command', None)
    if not manifest_command:
        print_error("Please specify a manifest subcommand: rebuild")
        sys.exit(1)

    handlers = {
        'rebuild': _cmd_manifest_rebuild,
    }

    handler = handlers.get(manifest_command)
    if handler is None:
        print_error(f"Unknown manifest subcommand: {manifest_command}")
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

    # Get parameters
    ratio = getattr(args, 'ratio', 0.5)
    min_chars = getattr(args, 'min_chars', 200)

    done_tasks = _collect_status_tasks(storage, [TaskStatus.DONE, TaskStatus.ARCHIVED])
    done_lengths = [length for _, length in done_tasks]

    if done_lengths:
        done_median = statistics.median(done_lengths)
        threshold = max(int(done_median * ratio), min_chars)
    else:
        done_median = None
        fallback_done = 1000
        threshold = max(int(fallback_done * ratio), min_chars, 500)

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
        return

    for task, length in stub_tasks:
        if length < threshold:
            short_tasks.append((task, length))

    if short_tasks:
        print_warning(
            f"{len(short_tasks)} stub task(s) need more detail (< {threshold} chars):",
            "Needs Detail"
        )
        for task, length in sorted(short_tasks, key=lambda x: x[1]):
            print(f"  • {task.id}: {task.title} ({length} chars)")
    else:
        print_success(f"All {len(stub_tasks)} stub tasks meet detail threshold", "Groom Check")


def _session_start(storage: TaskStorage, args):
    state_path, _, sequence_path = _session_paths(storage)
    if state_path.exists():
        active = _load_json(state_path) or {}
        session_id = active.get("session_id", "unknown")
        print_error(f"Session {session_id} is already active. End it before starting a new one.")
        sys.exit(1)

    session_id = _next_session_id(sequence_path)
    now = utc_now().isoformat()
    session = {
        "session_id": session_id,
        "started": now,
        "focus": getattr(args, "focus", None),
        "primary_task": getattr(args, "task", None),
        "notes": getattr(args, "notes", None),
        "commits": [],
    }
    session = {k: v for k, v in session.items() if v not in (None, "", [])}

    _write_json(state_path, session)

    print_success(f"Started session {session_id}", "Session Started")
    if session.get("focus"):
        print_info(f"Focus: {session['focus']}")
    print_info("Use `taskpy session end` to close the session when finished.")


def _session_end(storage: TaskStorage, args):
    state_path, log_path, _ = _session_paths(storage)
    active = _load_json(state_path)

    if not active:
        print_warning("No active session to end.")
        return

    now = utc_now()
    active["ended"] = now.isoformat()
    started = active.get("started")
    duration_seconds = 0
    if started:
        try:
            start_dt = datetime.fromisoformat(started)
            duration_seconds = int((now - start_dt).total_seconds())
        except ValueError:
            duration_seconds = 0
    active["duration_seconds"] = max(duration_seconds, 0)

    closing_notes = getattr(args, "notes", None)
    if closing_notes:
        if active.get("notes"):
            active["notes"] = f"{active['notes']}\n{closing_notes}"
        else:
            active["notes"] = closing_notes

    _append_session_log(log_path, active)
    state_path.unlink(missing_ok=True)

    print_success(
        f"Ended session {active.get('session_id')} "
        f"({_format_duration(active['duration_seconds'])})",
        "Session Ended"
    )


def _session_status(storage: TaskStorage):
    state_path, _, _ = _session_paths(storage)
    active = _load_json(state_path)

    if not active:
        print_info("No active session. Start one with: taskpy session start --focus \"<focus>\"")
        return

    started = active.get("started")
    elapsed = 0
    if started:
        try:
            start_dt = datetime.fromisoformat(started)
            elapsed = int((utc_now() - start_dt).total_seconds())
        except ValueError:
            elapsed = 0

    print_success(f"Active session: {active.get('session_id')}", "Session Status")
    if started:
        print_info(f"Started: {started}")
    if active.get("focus"):
        print_info(f"Focus: {active['focus']}")
    if active.get("primary_task"):
        print_info(f"Primary task: {active['primary_task']}")
    if elapsed:
        print_info(f"Elapsed: {_format_duration(elapsed)}")
    if active.get("commits"):
        print_info(f"Commits logged: {len(active['commits'])}")


def _session_list(storage: TaskStorage, limit: int):
    _, log_path, _ = _session_paths(storage)
    if not log_path.exists():
        print_info("No sessions recorded yet.")
        return

    entries: List[Dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not entries:
        print_info("No sessions recorded yet.")
        return

    limit = limit if limit and limit > 0 else len(entries)
    recent = entries[-limit:]
    print_success(f"Last {len(recent)} session(s)", "Session Log")
    for session in reversed(recent):
        session_id = session.get("session_id", "session")
        start = session.get("started", "unknown")
        duration = _format_duration(session.get("duration_seconds", 0))
        focus = session.get("focus") or "N/A"
        print(f"- {session_id}: {start} ({duration}) | Focus: {focus}")


def _session_commit(storage: TaskStorage, args):
    state_path, _, _ = _session_paths(storage)
    active = _load_json(state_path)
    if not active:
        print_error("No active session. Start one before logging commits.")
        sys.exit(1)

    commit_hash = getattr(args, "commit_hash", None)
    message_parts = getattr(args, "message", [])
    if not commit_hash or not message_parts:
        print_error("Commit hash and message are required.")
        sys.exit(1)

    commit_entry = {
        "hash": commit_hash,
        "message": " ".join(message_parts),
        "timestamp": utc_now().isoformat(),
    }
    active.setdefault("commits", []).append(commit_entry)
    _write_json(state_path, active)

    print_success(f"Logged commit {commit_hash} for {active.get('session_id')}")


def cmd_session(args):
    """Manage work sessions with start/stop/status/list/commit helpers."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    command = getattr(args, "session_command", "status")

    if command == 'start':
        _session_start(storage, args)
    elif command in {'end', 'stop'}:
        _session_end(storage, args)
    elif command == 'status':
        _session_status(storage)
    elif command == 'list':
        limit = getattr(args, 'limit', 5)
        _session_list(storage, limit)
    elif command == 'commit':
        _session_commit(storage, args)
    else:
        print_error(f"Unknown session subcommand: {command}")
        sys.exit(1)


def cmd_overrides(args):
    """View override usage history aggregated from task histories."""
    storage = get_storage()

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    # Collect all override entries from all tasks
    override_entries = []

    # Scan all status directories for tasks
    for status_dir in storage.status_dir.iterdir():
        if not status_dir.is_dir():
            continue

        for task_file in status_dir.glob('*.md'):
            try:
                task = storage.read_task_file(task_file)

                # Extract override entries from task history
                # Note: Accept both 'override' and legacy 'override_*' actions for backward compat
                if task.history:
                    for entry in task.history:
                        if entry.action == 'override' or entry.action.startswith('override_'):
                            override_entries.append({
                                'timestamp': entry.timestamp,
                                'task_id': task.id,
                                'from_status': entry.from_status or 'unknown',
                                'to_status': entry.to_status or 'unknown',
                                'reason': entry.reason or 'No reason provided'
                            })
            except Exception as exc:
                # Skip tasks that can't be read
                print_warning(f"Could not read {task_file.name}: {exc}")
                continue

    if not override_entries:
        print_info("No overrides logged yet")
        print("Override history is now tracked in task histories.")
        print("Use: taskpy history TASK-ID  to see individual task overrides")
        return

    # Sort by timestamp (most recent first)
    override_entries.sort(key=lambda x: x['timestamp'], reverse=True)

    print(f"\n{'='*80}")
    print(f"Override History ({len(override_entries)} total)")
    print(f"{'='*80}\n")

    # Display entries in same format as before
    for entry in override_entries:
        timestamp_str = entry['timestamp'].strftime("%Y-%m-%dT%H:%M:%S")
        transition = f"{entry['from_status']}→{entry['to_status']}"
        print(f"{timestamp_str} | {entry['task_id']} | {transition} | Reason: {entry['reason']}")

    print()


__all__ = ['cmd_init', 'cmd_verify', 'cmd_manifest', 'cmd_groom', 'cmd_session', 'cmd_overrides']
