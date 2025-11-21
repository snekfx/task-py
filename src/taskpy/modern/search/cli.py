"""CLI registration for search command."""

import argparse
from .commands import cmd_search


def register():
    return {
        "search": {
            "func": cmd_search,
            "help": "Search tasks by keyword and tags",
            "parser": setup_search_parser,
        }
    }


def setup_search_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        "search",
        help="Search tasks by keyword and tags",
    )
    parser.add_argument("keywords", nargs="+", help="Keywords to search for (AND matching)")
    parser.add_argument("--filter", dest="filters", help="Comma-separated fields to search (title,body,tags,id,epic,status)")
    parser.add_argument("--status", help="Comma-separated statuses to include (e.g., active,qa,done)")
    parser.add_argument("--epic", help="Filter by epic (e.g., FEAT)")
    parser.add_argument("--in-sprint", action="store_true", help="Limit to in-sprint tasks")
    parser.add_argument("--archived", action="store_true", help="Include archived tasks in results")
    return parser


__all__ = ["register"]
