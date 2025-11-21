"""CLI registration for tags management."""

import argparse

from .commands import cmd_tags


def register():
    return {
        "tags": {
            "func": cmd_tags,
            "help": "Manage task tags (list/add/remove/set/clear)",
            "parser": setup_tags_parser,
        }
    }


def setup_tags_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "tags",
        help="List or update tags on tasks",
    )
    parser.add_argument("task_ids", nargs="+", help="Task IDs (space/comma separated)")
    parser.add_argument("--list", action="store_true", help="List tags (default)")
    parser.add_argument("--add", help="Comma-separated tags to add")
    parser.add_argument("--remove", help="Comma-separated tags to remove")
    parser.add_argument("--set", dest="set_tags", help="Comma-separated tags to replace existing tags")
    parser.add_argument("--clear", action="store_true", help="Clear all tags")
    return parser


__all__ = ["register"]
