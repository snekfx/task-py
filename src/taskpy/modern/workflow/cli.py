"""CLI registration for workflow features."""

import argparse
from taskpy.modern.shared.utils import add_reason_argument
from .commands import cmd_promote, cmd_demote, cmd_move, cmd_resolve


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
        },
        'resolve': {
            'func': cmd_resolve,
            'help': 'Resolve bug tasks with special resolution types',
            'parser': setup_resolve_parser,
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
    parser.add_argument('--signoff', action='store_true', help='Confirm signoff when archiving done tasks')
    parser.add_argument('--override', action='store_true', help='Override gate validation (logged)')
    add_reason_argument(
        parser,
        required=False,
        help_text='Reason for override (recommended with --override); required when archiving without signoff list',
    )

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
    add_reason_argument(
        parser,
        required=False,
        help_text='Reason for demotion (required for done→qa)',
    )
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
    add_reason_argument(
        parser,
        required=True,
        help_text='Reason for move (required)',
    )

    return parser


def setup_resolve_parser(subparsers):
    parser = subparsers.add_parser(
        'resolve',
        help='Resolve BUGS/REG/DEF tasks with resolution types'
    )
    parser.add_argument('task_id', help='Bug-like task ID (BUGS-*, REG-*, DEF-*)')
    parser.add_argument(
        '--resolution',
        required=True,
        choices=['fixed', 'duplicate', 'cannot_reproduce', 'wont_fix', 'config_change', 'docs_only'],
        help='Resolution type'
    )
    add_reason_argument(parser, required=True, help_text='Explanation for this resolution')
    parser.add_argument('--duplicate-of', help='Required when --resolution duplicate')
    return parser


__all__ = ['register']
