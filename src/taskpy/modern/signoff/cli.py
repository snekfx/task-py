"""CLI registration for signoff list management."""

import argparse

from .commands import cmd_signoff


def register():
    return {
        "signoff": {
            "func": cmd_signoff,
            "help": "Manage signoff tickets for archival gating",
            "parser": setup_signoff_parser,
        }
    }


def setup_signoff_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "signoff",
        help="Manage signoff tickets (list/add/remove)",
    )
    parser.set_defaults(signoff_action="list")

    signoff_sub = parser.add_subparsers(dest="signoff_action", help="Signoff actions")

    signoff_sub.add_parser("list", help="List signed-off tickets")

    add_parser = signoff_sub.add_parser("add", help="Add tickets to signoff list")
    add_parser.add_argument("task_ids", nargs="+", help="Task IDs (space or comma separated)")

    remove_parser = signoff_sub.add_parser("remove", help="Remove tickets from signoff list")
    remove_parser.add_argument("task_ids", nargs="+", help="Task IDs (space or comma separated)")

    return parser


__all__ = ["register"]
