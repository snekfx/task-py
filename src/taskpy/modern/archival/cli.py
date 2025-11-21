"""CLI registration for archival commands."""

import argparse

from .commands import cmd_archive


def register():
    return {
        "archive": {
            "func": cmd_archive,
            "help": "Archive done tasks with signoff gating",
            "parser": setup_archive_parser,
        }
    }


def setup_archive_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "archive",
        help="Archive done tasks (done -> archived) with optional bulk support",
    )
    parser.add_argument("task_ids", nargs="*", help="Task IDs (space/comma separated)")
    parser.add_argument("--all-done", action="store_true", help="Archive all done tasks")
    parser.add_argument("--signoff", action="store_true", help="Confirm signoff and allow archive")
    parser.add_argument("--reason", help="Reason for signoff/archival (required when bypassing list in non-strict mode)")
    parser.add_argument("--yes", action="store_true", help="Proceed without confirmation for bulk actions")
    parser.add_argument("--dry-run", action="store_true", help="Preview archival targets without modifying files")
    return parser


__all__ = ["register"]
