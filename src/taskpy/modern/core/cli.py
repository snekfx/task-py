"""CLI registration for core task management."""

import argparse
from .commands import cmd_list


def register():
    """Register core commands with main CLI.

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
        'list': {
            'func': cmd_list,
            'help': 'List tasks with optional filters',
            'parser': setup_parser
        }
    }


def setup_parser(subparsers):
    """Setup argument parser for list command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for list command
    """
    parser = subparsers.add_parser(
        'list',
        help='List tasks with optional filters'
    )

    # Filtering options
    parser.add_argument('--status', help='Filter by status')
    parser.add_argument('--epic', help='Filter by epic')
    parser.add_argument('--priority', help='Filter by priority')
    parser.add_argument('--milestone', help='Filter by milestone')
    parser.add_argument('--sprint', action='store_true', help='Show only sprint tasks')
    parser.add_argument('--all', action='store_true', help='Show all tasks including done/archived')

    # Sorting
    parser.add_argument('--sort',
                       choices=['priority', 'status', 'sp', 'created', 'updated'],
                       default='priority',
                       help='Sort order')

    return parser


__all__ = ['register']
