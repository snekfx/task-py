"""CLI registration for blocking/dependencies."""

from taskpy.modern.shared.utils import add_reason_argument
from .commands import cmd_block, cmd_unblock


def register():
    """Register blocking commands with main CLI."""
    return {
        'block': {
            'func': cmd_block,
            'help': 'Block a task with a required reason',
            'parser': _setup_block_parser,
        },
        'unblock': {
            'func': cmd_unblock,
            'help': 'Unblock a task and return it to backlog',
            'parser': _setup_unblock_parser,
        },
    }


def _setup_block_parser(subparsers):
    parser = subparsers.add_parser(
        'block',
        help='Block task(s) with a required reason',
    )
    parser.add_argument(
        'task_ids',
        nargs='+',
        help='Task ID(s) to block (comma or space separated)',
    )
    add_reason_argument(
        parser,
        required=True,
        help_text='Reason for blocking (required)',
    )
    return parser


def _setup_unblock_parser(subparsers):
    parser = subparsers.add_parser(
        'unblock',
        help='Unblock task(s) and move them back to backlog',
    )
    parser.add_argument(
        'task_ids',
        nargs='+',
        help='Task ID(s) to unblock (comma or space separated)',
    )
    return parser
