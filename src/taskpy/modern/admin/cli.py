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
        help='Manage work sessions'
    )
    parser.set_defaults(session_command='status')

    session_subparsers = parser.add_subparsers(
        dest='session_command',
        help='Session subcommands'
    )

    start_parser = session_subparsers.add_parser(
        'start',
        help='Start a new work session'
    )
    start_parser.add_argument('--focus', help='Primary focus or description for this session')
    start_parser.add_argument('--task', help='Primary task ID for this session')
    start_parser.add_argument('--notes', help='Optional notes captured when starting the session')

    end_parser = session_subparsers.add_parser(
        'end',
        help='End the active session and log it'
    )
    end_parser.add_argument('--notes', help='Summary notes appended when ending the session')

    stop_parser = session_subparsers.add_parser(
        'stop',
        help='Alias for end'
    )
    stop_parser.add_argument('--notes', help='Summary notes appended when ending the session')

    session_subparsers.add_parser(
        'status',
        help='Show the current session status (default)'
    )

    list_parser = session_subparsers.add_parser(
        'list',
        help='List recent sessions from the session log'
    )
    list_parser.add_argument('--limit', type=int, default=5,
                             help='Number of entries to show (default: 5)')

    commit_parser = session_subparsers.add_parser(
        'commit',
        help='Record a commit hash/message for the active session'
    )
    commit_parser.add_argument('commit_hash', help='Commit hash to record')
    commit_parser.add_argument('message', nargs='+', help='Commit message/notes')

    return parser


def setup_overrides_parser(subparsers):
    """Setup argument parser for overrides command."""
    parser = subparsers.add_parser(
        'overrides',
        help='View override usage history'
    )

    return parser


__all__ = ['register']
