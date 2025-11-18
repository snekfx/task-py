"""CLI registration for display features."""

import argparse
from .commands import cmd_info, cmd_stoplight, cmd_kanban, cmd_history, cmd_stats


def register():
    """Register display commands with main CLI.

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
        'info': {
            'func': cmd_info,
            'help': 'Show task status and gate requirements',
            'parser': setup_info_parser
        },
        'stoplight': {
            'func': cmd_stoplight,
            'help': 'Validate gates with exit codes (for CI)',
            'parser': setup_stoplight_parser
        },
        'kanban': {
            'func': cmd_kanban,
            'help': 'Display kanban board',
            'parser': setup_kanban_parser
        },
        'history': {
            'func': cmd_history,
            'help': 'Show task history/audit trail',
            'parser': setup_history_parser
        },
        'stats': {
            'func': cmd_stats,
            'help': 'Show project statistics',
            'parser': setup_stats_parser
        }
    }


def setup_info_parser(subparsers):
    """Setup argument parser for info command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for info command
    """
    parser = subparsers.add_parser(
        'info',
        help='Show task status and gate requirements'
    )
    parser.add_argument('task_id', help='Task ID')

    return parser


def setup_stoplight_parser(subparsers):
    """Setup argument parser for stoplight command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for stoplight command
    """
    parser = subparsers.add_parser(
        'stoplight',
        help='Validate gates with exit codes (0=ready, 1=blocked, 2=error)'
    )
    parser.add_argument('task_id', help='Task ID')

    return parser


def setup_kanban_parser(subparsers):
    """Setup argument parser for kanban command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for kanban command
    """
    parser = subparsers.add_parser(
        'kanban',
        help='Display kanban board'
    )
    parser.add_argument('--epic', help='Filter by epic')
    parser.add_argument('--sort', choices=['priority', 'created', 'updated', 'id'],
                        default='priority', help='Sort mode (default: priority)')

    return parser


def setup_history_parser(subparsers):
    """Setup argument parser for history command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for history command
    """
    parser = subparsers.add_parser(
        'history',
        help='Show task history/audit trail'
    )
    parser.add_argument('task_id', nargs='?', help='Task ID (omit for --all mode)')
    parser.add_argument('--all', action='store_true', help='Show history for all tasks')

    return parser


def setup_stats_parser(subparsers):
    """Setup argument parser for stats command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for stats command
    """
    parser = subparsers.add_parser(
        'stats',
        help='Show project statistics'
    )
    parser.add_argument('--epic', help='Filter by epic')
    parser.add_argument('--milestone', help='Filter by milestone')

    return parser


__all__ = ['register']
