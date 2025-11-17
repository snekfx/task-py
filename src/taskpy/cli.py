"""
CLI interface for TaskPy.

Command-line argument parsing and command routing.
"""

import argparse
import sys
from pathlib import Path

from taskpy import __version__
from taskpy.output import OutputMode, set_output_mode


class VersionAction(argparse.Action):
    """Custom version action that displays logo and version info."""

    def __call__(self, parser, namespace, values, option_string=None):
        # Read logo from package directory (bundled with the package)
        logo_path = Path(__file__).parent / "logo.txt"
        try:
            with open(logo_path, "r") as f:
                logo = f.read().rstrip()
            print(logo)
        except Exception:
            # Fallback if logo not found
            pass

        print(f"Version: {__version__} | License: AGPLv3")
        print("Copyright © 2025 Qodeninja/SnekFX")
        parser.exit()


class HelpAction(argparse.Action):
    """Custom help action that displays logo, version, and help."""

    def __call__(self, parser, namespace, values, option_string=None):
        # Display logo and version
        logo_path = Path(__file__).parent / "logo.txt"
        try:
            with open(logo_path, "r") as f:
                logo = f.read().rstrip()
            print(logo)
        except Exception:
            pass

        print(f"Version: {__version__} | License: AGPLv3")
        print("Copyright © 2025 Qodeninja/SnekFX")
        print()

        # Display help
        parser.print_help()
        parser.exit()


def _create_global_parser() -> argparse.ArgumentParser:
    """
    Create parser with options shared between root parser and subcommands.

    This allows flags to work in both positions:
    - taskpy --agent list
    - taskpy list --agent
    """
    global_parser = argparse.ArgumentParser(add_help=False)

    global_parser.add_argument(
        "-v", "--version",
        action=VersionAction,
        nargs=0,
        default=argparse.SUPPRESS,
        help="Show version and logo"
    )

    global_parser.add_argument(
        "--view",
        choices=["pretty", "data"],
        default=argparse.SUPPRESS,
        help="Output mode: pretty (boxy) or data (plain)"
    )

    global_parser.add_argument(
        "--data",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Plain data output (same as --view=data)"
    )

    global_parser.add_argument(
        "--no-boxy",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Disable boxy output (same as --view=data)"
    )

    global_parser.add_argument(
        "--agent",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Agent-friendly output (same as --view=data)"
    )

    global_parser.add_argument(
        "--all",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Show all items including done/archived (for list/history commands)"
    )

    return global_parser


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    from taskpy.help import MAIN_EPILOG, COMMAND_HELP

    global_parser = _create_global_parser()

    parser = argparse.ArgumentParser(
        prog="taskpy",
        description="File-based agile task management for META PROCESS v4",
        epilog=MAIN_EPILOG,
        parents=[global_parser],
        add_help=False,  # We'll add custom help action
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add custom help action
    parser.add_argument(
        "-h", "--help",
        action=HelpAction,
        nargs=0,
        default=argparse.SUPPRESS,
        help="Show this help message and exit"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    def add_subparser(name: str, **kwargs) -> argparse.ArgumentParser:
        """Helper that attaches global options to each subparser."""
        # Use command help from help.py if available
        if 'help' not in kwargs and name in COMMAND_HELP:
            kwargs['help'] = COMMAND_HELP[name]
        return subparsers.add_parser(
            name,
            parents=[global_parser],
            add_help=True,
            **kwargs
        )

    # taskpy init
    init_parser = add_subparser("init")
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Reinitialize even if already initialized"
    )
    init_parser.add_argument(
        "--type",
        choices=["rust", "python", "node", "shell", "generic"],
        help="Explicitly set project type (default: auto-detect)"
    )

    # taskpy create <EPIC> <title>
    create_parser = add_subparser(
        "create",
        help="Create a new task"
    )
    create_parser.add_argument(
        "epic",
        help="Epic name (e.g., BUGS, DOCS, FEAT)"
    )
    create_parser.add_argument(
        "title",
        nargs="+",
        help="Task title"
    )
    create_parser.add_argument(
        "--sp", "--story-points",
        type=int,
        default=0,
        dest="story_points",
        help="Story points estimate"
    )
    create_parser.add_argument(
        "--priority",
        choices=["critical", "high", "medium", "low"],
        default="medium",
        help="Task priority"
    )
    create_parser.add_argument(
        "--status",
        choices=["stub", "backlog", "ready", "active", "qa", "blocked"],
        default="stub",
        help="Initial status (default: stub for incomplete tasks)"
    )
    create_parser.add_argument(
        "--tags",
        help="Comma-separated tags"
    )
    create_parser.add_argument(
        "--milestone",
        help="Assign to milestone (e.g., milestone-1)"
    )
    create_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open task in $EDITOR after creation"
    )
    create_parser.add_argument(
        "--body",
        help="Task body/description content"
    )
    create_parser.add_argument(
        "--stub",
        action="store_true",
        help="Allow creation in stub status without body"
    )

    # taskpy list [filters]
    list_parser = add_subparser(
        "list",
        help="List tasks with optional filters"
    )
    list_parser.add_argument(
        "--epic",
        help="Filter by epic"
    )
    list_parser.add_argument(
        "--status",
        help="Filter by status"
    )
    list_parser.add_argument(
        "--priority",
        help="Filter by priority"
    )
    list_parser.add_argument(
        "--tags",
        help="Filter by tags (comma-separated)"
    )
    list_parser.add_argument(
        "--assigned",
        help="Filter by assigned user/session"
    )
    list_parser.add_argument(
        "--milestone",
        help="Filter by milestone (e.g., milestone-1)"
    )
    list_parser.add_argument(
        "--sprint",
        action="store_true",
        help="Filter to sprint tasks only"
    )
    list_parser.add_argument(
        "--format",
        choices=["table", "cards", "ids", "tsv"],
        default="table",
        help="Output format"
    )
    list_parser.add_argument(
        "--sort",
        choices=["priority", "created", "id", "status"],
        default="priority",
        help="Sort order: priority (default), created (chronological), id (task ID), status (workflow stage)"
    )
    # Note: --all is now a global flag, defined in global_parser
    # Keep --show-all as alias for backward compatibility
    list_parser.add_argument(
        "--show-all",
        dest="all",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS  # Hidden alias
    )

    # taskpy show <TASK-ID>
    show_parser = add_subparser(
        "show",
        help="Display one or more tasks"
    )
    show_parser.add_argument(
        "task_ids",
        nargs='+',
        help="One or more task IDs (e.g., BUGS-001 or BUGS-001,BUGS-002 or BUGS-001 BUGS-002)"
    )

    # taskpy edit <TASK-ID>
    edit_parser = add_subparser(
        "edit",
        help="Edit a task in $EDITOR"
    )
    edit_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy promote <TASK-ID> [--to STATUS]
    promote_parser = add_subparser(
        "promote",
        help="Move task forward in workflow"
    )
    promote_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    promote_parser.add_argument(
        "--to",
        dest="target_status",
        help="Target status (default: next in workflow)"
    )
    promote_parser.add_argument(
        "--commit",
        help="Git commit hash (required for qa → done)"
    )
    promote_parser.add_argument(
        "--override",
        action="store_true",
        help="Bypass gate validation (use only in urgent situations)"
    )
    promote_parser.add_argument(
        "--reason",
        help="Reason for override (recommended when using --override)"
    )

    # taskpy demote <TASK-ID> [--to STATUS] --reason REASON
    demote_parser = add_subparser(
        "demote",
        help="Move task backwards in workflow"
    )
    demote_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    demote_parser.add_argument(
        "--to",
        help="Target status (default: previous in workflow)"
    )
    demote_parser.add_argument(
        "--reason",
        help="Reason for demotion (required when demoting from done)"
    )
    demote_parser.add_argument(
        "--override",
        action="store_true",
        help="Bypass gate validation (use only in urgent situations)"
    )

    # taskpy info <TASK-ID>
    info_parser = add_subparser(
        "info",
        help="Show task status and gate requirements"
    )
    info_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy stoplight <TASK-ID>
    stoplight_parser = add_subparser(
        "stoplight",
        help="Validate gate requirements (exit codes: 0=ready, 1=missing, 2=blocked)"
    )
    stoplight_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy block <TASK-ID> --reason REASON
    block_parser = add_subparser(
        "block",
        help="Block a task with required reason"
    )
    block_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    block_parser.add_argument(
        "--reason",
        required=True,
        help="Reason for blocking (required)"
    )

    # taskpy unblock <TASK-ID>
    unblock_parser = add_subparser(
        "unblock",
        help="Unblock a task and return to backlog"
    )
    unblock_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy move <TASK-ID> <STATUS>
    move_parser = add_subparser(
        "move",
        help="Move task(s) to specific status"
    )
    move_parser.add_argument(
        "task_ids",
        nargs='+',
        help="One or more task IDs (e.g., BUGS-001 or BUGS-001,BUGS-002 or BUGS-001 BUGS-002)"
    )
    move_parser.add_argument(
        "status",
        choices=["stub", "backlog", "ready", "active", "qa", "regression", "done", "archived", "blocked"],
        help="Target status"
    )
    move_parser.add_argument(
        "--reason",
        required=True,
        help="Reason for moving task (required)"
    )

    # taskpy kanban
    kanban_parser = add_subparser(
        "kanban",
        help="Display kanban board"
    )
    kanban_parser.add_argument(
        "--epic",
        help="Filter by epic"
    )
    kanban_parser.add_argument(
        "--sort",
        choices=["priority", "created", "id", "status"],
        default="priority",
        help="Sort order: priority (default), created (chronological), id (task ID), status (workflow stage)"
    )

    # taskpy verify <TASK-ID>
    verify_parser = add_subparser(
        "verify",
        help="Run verification tests for a task"
    )
    verify_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    verify_parser.add_argument(
        "--update",
        action="store_true",
        help="Update verification status in task"
    )

    # taskpy epics
    epics_parser = add_subparser(
        "epics",
        help="List available epics"
    )
    epics_parser.add_argument(
        "--add",
        metavar="NAME",
        help="Add a new epic"
    )

    # taskpy nfrs
    nfrs_parser = add_subparser(
        "nfrs",
        help="List NFRs"
    )
    nfrs_parser.add_argument(
        "--defaults",
        action="store_true",
        help="Show only default NFRs"
    )

    # taskpy milestones
    milestones_parser = add_subparser(
        "milestones",
        help="List project milestones"
    )

    # taskpy milestone (with subcommands)
    milestone_parser = add_subparser(
        "milestone",
        help="Manage individual milestones"
    )
    milestone_subparsers = milestone_parser.add_subparsers(dest="milestone_command")

    milestone_show = milestone_subparsers.add_parser("show", help="Show milestone details and stats")
    milestone_show.add_argument("milestone_id", help="Milestone ID (e.g., milestone-1)")

    milestone_start = milestone_subparsers.add_parser("start", help="Mark milestone as active")
    milestone_start.add_argument("milestone_id", help="Milestone ID (e.g., milestone-1)")

    milestone_complete = milestone_subparsers.add_parser("complete", help="Mark milestone as completed")
    milestone_complete.add_argument("milestone_id", help="Milestone ID (e.g., milestone-1)")

    milestone_assign = milestone_subparsers.add_parser("assign", help="Assign task to milestone")
    milestone_assign.add_argument("task_id", help="Task ID (e.g., FEAT-01)")
    milestone_assign.add_argument("milestone_id", help="Milestone ID (e.g., milestone-1)")

    # taskpy link <TASK-ID>
    link_parser = add_subparser(
        "link",
        help="Link references to a task"
    )
    link_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    link_parser.add_argument(
        "--code",
        action="append",
        help="Link code file (can specify multiple)"
    )
    link_parser.add_argument(
        "--docs",
        action="append",
        help="Link documentation (can specify multiple)"
    )
    link_parser.add_argument(
        "--plan",
        action="append",
        help="Link plan document (can specify multiple)"
    )
    link_parser.add_argument(
        "--test",
        action="append",
        help="Link test file (can specify multiple)"
    )
    link_parser.add_argument(
        "--nfr",
        action="append",
        help="Link NFR (can specify multiple)"
    )
    link_parser.add_argument(
        "--verify",
        action="append",
        help="Link verification command (can specify multiple)"
    )
    link_parser.add_argument(
        "--issue",
        action="append",
        help="Add issue annotation (appends to ISSUES section with timestamp)"
    )
    link_parser.add_argument(
        "--commit",
        help="Link git commit hash"
    )

    # taskpy issues <TASK-ID>
    issues_parser = add_subparser(
        "issues",
        help="Display issues/problems tracked for a task"
    )
    issues_parser.add_argument(
        "task_id",
        help="Task ID (e.g., FEAT-01)"
    )

    # taskpy history <TASK-ID> or taskpy history --all
    history_parser = add_subparser(
        "history",
        help="Display task history and audit trail"
    )
    history_parser.add_argument(
        "task_id",
        nargs="?",
        help="Task ID (e.g., FEAT-01) - omit to show all with --all"
    )
    # Note: --all is now a global flag, defined in global_parser

    # taskpy resolve <TASK-ID> --resolution TYPE --reason REASON
    resolve_parser = add_subparser(
        "resolve",
        help="Resolve a bug task (BUGS*, REG*, DEF*) with special resolution"
    )
    resolve_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001, REG-05, DEF-10)"
    )
    resolve_parser.add_argument(
        "--resolution",
        required=True,
        choices=["fixed", "duplicate", "cannot_reproduce", "wont_fix", "config_change", "docs_only"],
        help="Resolution type"
    )
    resolve_parser.add_argument(
        "--reason",
        required=True,
        help="Explanation for this resolution"
    )
    resolve_parser.add_argument(
        "--duplicate-of",
        help="Reference to duplicate task (used with --resolution duplicate)"
    )

    # taskpy delete <TASK-ID> --reason REASON
    delete_parser = add_subparser(
        "delete",
        help="Move task to trash (soft delete, recoverable)"
    )
    delete_parser.add_argument(
        "task_id",
        help="Task ID (e.g., FEAT-001)"
    )
    delete_parser.add_argument(
        "--reason",
        required=True,
        help="Reason for deletion (logged in history)"
    )

    # taskpy trash [empty]
    trash_parser = add_subparser(
        "trash",
        help="View or empty trash bin"
    )
    trash_parser.add_argument(
        "action",
        nargs="?",
        choices=["empty"],
        help="Optional: 'empty' to permanently delete all trashed tasks"
    )

    # taskpy recover <AUTO-ID> --reason REASON
    recover_parser = add_subparser(
        "recover",
        help="Recover task from trash by auto_id"
    )
    recover_parser.add_argument(
        "auto_id",
        type=int,
        help="Auto ID of trashed task (shown in trash list)"
    )
    recover_parser.add_argument(
        "--reason",
        required=True,
        help="Reason for recovery (logged in history)"
    )

    # taskpy rename <OLD-ID> <NEW-ID> [--skip-manifest] [--force]
    rename_parser = add_subparser(
        "rename",
        help="Rename task ID (change epic and/or number)"
    )
    rename_parser.add_argument(
        "old_id",
        help="Current task ID (e.g., QOL-12)"
    )
    rename_parser.add_argument(
        "new_id",
        help="New task ID (e.g., FEAT-12)"
    )
    rename_parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Skip manifest update (for internal use by recover)"
    )
    rename_parser.add_argument(
        "--force",
        action="store_true",
        help="Force rename even if new ID exists"
    )

    # taskpy tour
    tour_parser = add_subparser(
        "tour",
        help="Display TaskPy quick reference guide"
    )

    # taskpy help <topic>
    help_parser = add_subparser(
        "help",
        help="Display help and available commands"
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        choices=["dev", "stub", "active", "regression"],
        help="Workflow help topic (dev, stub, active, regression)"
    )

    # taskpy overrides
    overrides_parser = add_subparser(
        "overrides",
        help="View override usage history"
    )

    # taskpy manifest
    manifest_parser = add_subparser(
        "manifest",
        help="Manage the TSV manifest index"
    )
    manifest_subparsers = manifest_parser.add_subparsers(dest="manifest_command")
    manifest_subparsers.add_parser(
        "rebuild",
        help="Scan task files and rebuild manifest.tsv"
    )

    # taskpy groom
    groom_parser = add_subparser(
        "groom",
        help="Audit stub tasks for sufficient detail"
    )
    groom_parser.add_argument(
        "--ratio",
        type=float,
        default=0.6,
        help="Minimum ratio of stub content length vs done median (default: 0.6)"
    )
    groom_parser.add_argument(
        "--min-chars",
        type=int,
        default=500,
        help="Absolute minimum characters required for stub tasks"
    )
    groom_parser.add_argument(
        "--override",
        action="store_true",
        help="Acknowledge short tasks (report only, no warnings)"
    )

    # taskpy session
    session_parser = add_subparser(
        "session",
        help="Manage work sessions"
    )
    session_subparsers = session_parser.add_subparsers(dest="session_command")

    session_start = session_subparsers.add_parser("start", help="Start a work session")
    session_start.add_argument("--focus", help="Session focus description")

    session_end = session_subparsers.add_parser("end", help="End current session")
    session_end.add_argument("--notes", help="Session notes")

    session_status = session_subparsers.add_parser("status", help="Show current session")

    # taskpy sprint
    sprint_parser = add_subparser(
        "sprint",
        help="Manage sprint tasks (default: show dashboard)"
    )
    sprint_subparsers = sprint_parser.add_subparsers(dest="sprint_command")

    sprint_init = sprint_subparsers.add_parser("init", help="Initialize new sprint with metadata")
    sprint_init.add_argument("--title", help="Sprint title (e.g., 'Core Features Sprint')")
    sprint_init.add_argument("--focus", help="Sprint focus area (e.g., 'Testing and stability')")
    sprint_init.add_argument("--capacity", type=int, help="Sprint capacity in story points (default: 20)")
    sprint_init.add_argument("--duration", type=int, help="Sprint duration in days (default: 14)")
    sprint_init.add_argument("--force", action="store_true", help="Force overwrite existing sprint")

    sprint_add = sprint_subparsers.add_parser("add", help="Add task to sprint")
    sprint_add.add_argument("task_id", help="Task ID (e.g., FEAT-01)")

    sprint_remove = sprint_subparsers.add_parser("remove", help="Remove task from sprint")
    sprint_remove.add_argument("task_id", help="Task ID (e.g., FEAT-01)")

    sprint_list = sprint_subparsers.add_parser("list", help="List all sprint tasks")

    sprint_clear = sprint_subparsers.add_parser("clear", help="Clear all tasks from sprint")

    sprint_stats = sprint_subparsers.add_parser("stats", help="Show sprint statistics")

    sprint_recommend = sprint_subparsers.add_parser("recommend", help="Recommend tasks to add based on capacity and priority")

    # taskpy stats
    stats_parser = add_subparser(
        "stats",
        help="Show task statistics"
    )
    stats_parser.add_argument(
        "--epic",
        help="Filter by epic"
    )
    stats_parser.add_argument(
        "--milestone",
        help="Filter by milestone (e.g., milestone-1)"
    )

    return parser


def main():
    """Main entry point for taskpy CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle output mode (allow global flags anywhere)
    view_mode = getattr(args, "view", "pretty")
    data_flag = getattr(args, "data", False)
    no_boxy_flag = getattr(args, "no_boxy", False)
    agent_flag = getattr(args, "agent", False)

    # Normalize namespace so downstream handlers can rely on attributes
    args.view = view_mode
    args.data = data_flag
    args.no_boxy = no_boxy_flag
    args.agent = agent_flag

    if data_flag or no_boxy_flag or agent_flag or view_mode == "data":
        set_output_mode(OutputMode.DATA)
    else:
        set_output_mode(OutputMode.PRETTY)

    # Route to command handlers
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Import commands module (legacy)
    from taskpy.legacy import commands

    # Find and execute command
    command_name = args.command
    handler = getattr(commands, f"cmd_{command_name}", None)

    if handler is None:
        print(f"Error: Command '{command_name}' not implemented yet")
        sys.exit(1)

    try:
        handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
