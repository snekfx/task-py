"""CLI registration for admin features."""

import argparse
from .commands import cmd_init, cmd_verify, cmd_manifest, cmd_groom, cmd_session, cmd_overrides


def register():
    """Register admin commands with main CLI.

    Returns:
        dict: Command registration info
    """
    return {
        'init': {
            'func': cmd_init,
            'help': 'Initialize TaskPy kanban structure',
            'parser': setup_init_parser
        },
        'verify': {
            'func': cmd_verify,
            'help': 'Run verification tests for a task',
            'parser': setup_verify_parser
        },
        'manifest': {
            'func': cmd_manifest,
            'help': 'Manage manifest operations',
            'parser': setup_manifest_parser
        },
        'groom': {
            'func': cmd_groom,
            'help': 'Audit stub tasks for sufficient detail',
            'parser': setup_groom_parser
        },
        'session': {
            'func': cmd_session,
            'help': 'Manage work sessions',
            'parser': setup_session_parser
        },
        'overrides': {
            'func': cmd_overrides,
            'help': 'View override usage history',
            'parser': setup_overrides_parser
        }
    }


def setup_init_parser(subparsers):
    """Setup argument parser for init command."""
    parser = subparsers.add_parser(
        'init',
        help='Initialize TaskPy kanban structure'
    )
    parser.add_argument('--force', action='store_true', help='Force re-initialization')
    parser.add_argument('--type', help='Explicit project type (rust, python, node, etc.)')

    return parser


def setup_verify_parser(subparsers):
    """Setup argument parser for verify command."""
    parser = subparsers.add_parser(
        'verify',
        help='Run verification tests for a task'
    )
    parser.add_argument('task_id', help='Task ID')
    parser.add_argument('--update', action='store_true', help='Update verification status')

    return parser


def setup_manifest_parser(subparsers):
    """Setup argument parser for manifest command."""
    parser = subparsers.add_parser(
        'manifest',
        help='Manage manifest operations'
    )
    parser.add_argument('manifest_command', choices=['rebuild'], help='Manifest subcommand')

    return parser


def setup_groom_parser(subparsers):
    """Setup argument parser for groom command."""
    parser = subparsers.add_parser(
        'groom',
        help='Audit stub tasks for sufficient detail'
    )
    parser.add_argument('--ratio', type=float, default=0.5, help='Detail threshold ratio (default: 0.5)')
    parser.add_argument('--min-chars', type=int, default=200, help='Minimum characters (default: 200)')

    return parser


def setup_session_parser(subparsers):
    """Setup argument parser for session command."""
    parser = subparsers.add_parser(
        'session',
        help='Manage work sessions (coming soon)'
    )

    return parser


def setup_overrides_parser(subparsers):
    """Setup argument parser for overrides command."""
    parser = subparsers.add_parser(
        'overrides',
        help='View override usage history'
    )

    return parser


__all__ = ['register']
