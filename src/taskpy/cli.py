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
        # Read logo from root of package
        logo_path = Path(__file__).parent.parent.parent / "logo.txt"
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


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""

    parser = argparse.ArgumentParser(
        prog="taskpy",
        description="File-based agile task management for META PROCESS v4",
        epilog="For more information, see: README.md"
    )

    parser.add_argument(
        "-v", "--version",
        action=VersionAction,
        nargs=0,
        help="Show version and logo"
    )

    parser.add_argument(
        "--view",
        choices=["pretty", "data"],
        default="pretty",
        help="Output mode: pretty (boxy) or data (plain)"
    )

    parser.add_argument(
        "--no-boxy",
        action="store_true",
        help="Disable boxy output (same as --view=data)"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # taskpy init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize TaskPy kanban structure"
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Reinitialize even if already initialized"
    )

    # taskpy create <EPIC> <title>
    create_parser = subparsers.add_parser(
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
        choices=["backlog", "ready", "in_progress", "review"],
        default="backlog",
        help="Initial status"
    )
    create_parser.add_argument(
        "--tags",
        help="Comma-separated tags"
    )
    create_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open task in $EDITOR after creation"
    )

    # taskpy list [filters]
    list_parser = subparsers.add_parser(
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
        "--format",
        choices=["table", "cards", "ids", "tsv"],
        default="table",
        help="Output format"
    )

    # taskpy show <TASK-ID>
    show_parser = subparsers.add_parser(
        "show",
        help="Display a task"
    )
    show_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy edit <TASK-ID>
    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit a task in $EDITOR"
    )
    edit_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )

    # taskpy promote <TASK-ID> [--to STATUS]
    promote_parser = subparsers.add_parser(
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

    # taskpy move <TASK-ID> <STATUS>
    move_parser = subparsers.add_parser(
        "move",
        help="Move task to specific status"
    )
    move_parser.add_argument(
        "task_id",
        help="Task ID (e.g., BUGS-001)"
    )
    move_parser.add_argument(
        "status",
        choices=["backlog", "ready", "in_progress", "review", "done", "archived"],
        help="Target status"
    )

    # taskpy kanban
    kanban_parser = subparsers.add_parser(
        "kanban",
        help="Display kanban board"
    )
    kanban_parser.add_argument(
        "--epic",
        help="Filter by epic"
    )

    # taskpy verify <TASK-ID>
    verify_parser = subparsers.add_parser(
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
    epics_parser = subparsers.add_parser(
        "epics",
        help="List available epics"
    )
    epics_parser.add_argument(
        "--add",
        metavar="NAME",
        help="Add a new epic"
    )

    # taskpy nfrs
    nfrs_parser = subparsers.add_parser(
        "nfrs",
        help="List NFRs"
    )
    nfrs_parser.add_argument(
        "--defaults",
        action="store_true",
        help="Show only default NFRs"
    )

    # taskpy link <TASK-ID>
    link_parser = subparsers.add_parser(
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

    # taskpy session
    session_parser = subparsers.add_parser(
        "session",
        help="Manage work sessions"
    )
    session_subparsers = session_parser.add_subparsers(dest="session_command")

    session_start = session_subparsers.add_parser("start", help="Start a work session")
    session_start.add_argument("--focus", help="Session focus description")

    session_end = session_subparsers.add_parser("end", help="End current session")
    session_end.add_argument("--notes", help="Session notes")

    session_status = session_subparsers.add_parser("status", help="Show current session")

    # taskpy stats
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show task statistics"
    )
    stats_parser.add_argument(
        "--epic",
        help="Filter by epic"
    )

    return parser


def main():
    """Main entry point for taskpy CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle output mode
    if args.no_boxy or args.view == "data":
        set_output_mode(OutputMode.DATA)
    else:
        set_output_mode(OutputMode.PRETTY)

    # Route to command handlers
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Import commands module
    from taskpy import commands

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
