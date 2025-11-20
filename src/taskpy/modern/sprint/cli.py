"""CLI registration for sprint management."""

import argparse
from .commands import cmd_sprint


def register():
    """Register sprint commands with main CLI.

    Returns:
        dict: Command registration info with structure:
            {
                'command_name': {
                    'func': callable,
                    'help': str,
                    'parser': callable
                }
            }
    """
    return {
        'sprint': {
            'func': cmd_sprint,
            'help': 'Manage sprint tasks',
            'parser': setup_parser
        }
    }


def setup_parser(subparsers):
    """Setup argument parser for sprint command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for sprint command
    """
    parser = subparsers.add_parser(
        'sprint',
        help='Manage sprint tasks'
    )

    # Add subcommands
    sprint_subparsers = parser.add_subparsers(
        dest='sprint_subcommand',
        help='Sprint subcommands'
    )

    # list subcommand
    sprint_subparsers.add_parser(
        'list',
        help='List all tasks in sprint'
    )

    # dashboard subcommand
    sprint_subparsers.add_parser(
        'dashboard',
        help='Show sprint dashboard overview'
    )

    # add subcommand
    add_parser = sprint_subparsers.add_parser(
        'add',
        help='Add task to sprint'
    )
    add_parser.add_argument(
        'task_ids',
        nargs='+',
        help='Task ID(s) to add to sprint (comma/space separated)'
    )

    # remove subcommand
    remove_parser = sprint_subparsers.add_parser(
        'remove',
        help='Remove task from sprint'
    )
    remove_parser.add_argument(
        'task_ids',
        nargs='+',
        help='Task ID(s) to remove from sprint (comma/space separated)'
    )

    # clear subcommand
    sprint_subparsers.add_parser(
        'clear',
        help='Clear all tasks from sprint'
    )

    # stats subcommand
    sprint_subparsers.add_parser(
        'stats',
        help='Show sprint statistics'
    )

    # init subcommand
    init_parser = sprint_subparsers.add_parser(
        'init',
        help='Initialize a new sprint with metadata'
    )
    init_parser.add_argument('--title', help='Sprint title')
    init_parser.add_argument('--focus', help='Sprint focus area')
    init_parser.add_argument('--duration', type=int, default=14, help='Sprint duration in days (default: 14)')
    init_parser.add_argument('--capacity', type=int, default=20, help='Sprint capacity in story points (default: 20)')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing sprint')

    # recommend subcommand
    sprint_subparsers.add_parser(
        'recommend',
        help='Recommend tasks to add based on capacity and priority'
    )

    return parser


__all__ = ['register']
