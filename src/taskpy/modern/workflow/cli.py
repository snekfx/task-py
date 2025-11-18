"""CLI registration for workflow features."""

import argparse
from .commands import cmd_promote, cmd_demote, cmd_move


def register():
    """Register workflow commands with main CLI.

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
        'promote': {
            'func': cmd_promote,
            'help': 'Move task forward in workflow',
            'parser': setup_promote_parser
        },
        'demote': {
            'func': cmd_demote,
            'help': 'Move task backward in workflow',
            'parser': setup_demote_parser
        },
        'move': {
            'func': cmd_move,
            'help': 'Move task(s) to specific status',
            'parser': setup_move_parser
        }
    }


def setup_promote_parser(subparsers):
    """Setup argument parser for promote command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for promote command
    """
    parser = subparsers.add_parser(
        'promote',
        help='Move task forward in workflow'
    )
    parser.add_argument('task_id', help='Task ID to promote')
    parser.add_argument('--target-status', help='Target status (optional, defaults to next in workflow)')
    parser.add_argument('--commit', help='Commit hash (for qa→done promotion)')
    parser.add_argument('--override', action='store_true', help='Override gate validation (logged)')
    parser.add_argument('--reason', help='Reason for override (recommended with --override)')

    return parser


def setup_demote_parser(subparsers):
    """Setup argument parser for demote command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for demote command
    """
    parser = subparsers.add_parser(
        'demote',
        help='Move task backward in workflow'
    )
    parser.add_argument('task_id', help='Task ID to demote')
    parser.add_argument('--to', help='Target status (optional, defaults to previous in workflow)')
    parser.add_argument('--reason', help='Reason for demotion (required for done→qa)')
    parser.add_argument('--override', action='store_true', help='Override gate validation (logged)')

    return parser


def setup_move_parser(subparsers):
    """Setup argument parser for move command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for move command
    """
    parser = subparsers.add_parser(
        'move',
        help='Move task(s) to specific status'
    )
    parser.add_argument('task_ids', nargs='+', help='Task ID(s) to move (space or comma-separated)')
    parser.add_argument('status', help='Target status')
    parser.add_argument('--reason', required=True, help='Reason for move (required)')

    return parser


__all__ = ['register']
