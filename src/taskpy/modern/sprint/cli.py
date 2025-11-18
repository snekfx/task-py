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

    # Future subcommands: add, remove, clear, stats, init, recommend

    return parser


__all__ = ['register']
