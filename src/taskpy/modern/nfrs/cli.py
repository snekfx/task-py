"""CLI registration for NFRs feature."""

import argparse
from .commands import cmd_nfrs


def register():
    """Register NFRs commands with main CLI.

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
        'nfrs': {
            'func': cmd_nfrs,
            'help': 'List and manage non-functional requirements',
            'parser': setup_parser
        }
    }


def setup_parser(subparsers):
    """Setup argument parser for nfrs command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for nfrs command
    """
    parser = subparsers.add_parser(
        'nfrs',
        help='List and manage non-functional requirements'
    )

    parser.add_argument(
        '--defaults',
        action='store_true',
        help='Show only default NFRs'
    )

    return parser
