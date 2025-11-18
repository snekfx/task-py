"""CLI registration for epics feature."""

import argparse
from .commands import cmd_epics


def register():
    """Register epics commands with main CLI.

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
        'epics': {
            'func': cmd_epics,
            'help': 'List and manage epics',
            'parser': setup_parser
        }
    }


def setup_parser(subparsers):
    """Setup argument parser for epics command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for epics command
    """
    parser = subparsers.add_parser(
        'epics',
        help='List and manage epics'
    )

    # No additional args for now - just lists epics
    # Future: --add, --delete, --enable, --disable flags

    return parser


__all__ = ['register']
