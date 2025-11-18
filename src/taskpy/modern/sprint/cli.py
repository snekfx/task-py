"""CLI registration for sprint management."""

import argparse
from .commands import cmd_sprint_list


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
            'func': cmd_sprint_list,
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

    # For now just lists sprint tasks
    # Future: subcommands for add, remove, stats, etc.

    return parser


__all__ = ['register']
