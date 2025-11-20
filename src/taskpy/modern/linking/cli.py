"""CLI registration for task linking."""

import argparse

from .commands import cmd_link, cmd_issues


def register():
    """Register linking commands with main CLI."""
    return {
        'link': {
            'func': cmd_link,
            'help': 'Link references (code/docs/tests/issues) to a task',
            'parser': _setup_link_parser,
        },
        'issues': {
            'func': cmd_issues,
            'help': 'Display issues/problems tracked for a task',
            'parser': _setup_issues_parser,
        },
    }


def _setup_link_parser(subparsers):
    parser = subparsers.add_parser(
        'link',
        help='Attach references or issues to a task',
    )
    parser.add_argument(
        'task_ids',
        nargs='+',
        help='Task ID(s) (comma or space separated)',
    )
    parser.add_argument('--code', action='append', help='Code reference(s)')
    parser.add_argument('--docs', action='append', help='Docs reference(s)')
    parser.add_argument('--plan', action='append', help='Plan reference(s)')
    parser.add_argument('--test', action='append', help='Test reference(s)')
    parser.add_argument('--nfr', action='append', help='NFR reference(s)')
    parser.add_argument('--verify', action='append', help='Verification command')
    parser.add_argument('--commit', help='Commit hash')
    parser.add_argument('--issue', action='append', help='Record issue/problem description')
    return parser


def _setup_issues_parser(subparsers):
    parser = subparsers.add_parser(
        'issues',
        help='Display issues/problems tracked for a task',
    )
    parser.add_argument('task_id', help='Task ID to inspect')
    return parser
