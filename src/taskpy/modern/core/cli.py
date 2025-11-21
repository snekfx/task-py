"""CLI registration for core task management."""

import argparse
from .read import cmd_list, cmd_show
from .create import cmd_create
from .edit import cmd_edit
from .rename import cmd_rename
from .delete import cmd_delete
from .trash import cmd_trash
from .recover import cmd_recover


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
            'parser': setup_list_parser
        },
        'show': {
            'func': cmd_show,
            'help': 'Display task details',
            'parser': setup_show_parser
        },
        'create': {
            'func': cmd_create,
            'help': 'Create a new task',
            'parser': setup_create_parser
        },
        'edit': {
            'func': cmd_edit,
            'help': 'Edit a task in $EDITOR',
            'parser': setup_edit_parser
        },
        'rename': {
            'func': cmd_rename,
            'help': 'Rename a task ID',
            'parser': setup_rename_parser
        },
        'delete': {
            'func': cmd_delete,
            'help': 'Move a task to the trash (soft delete)',
            'parser': setup_delete_parser
        },
        'trash': {
            'func': cmd_trash,
            'help': 'View or empty the trash bin',
            'parser': setup_trash_parser
        },
        'recover': {
            'func': cmd_recover,
            'help': 'Recover a task from trash by auto_id',
            'parser': setup_recover_parser
        }
    }


def setup_list_parser(subparsers):
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
    parser.add_argument('--assigned', help='Filter by assigned user/session')
    parser.add_argument('--tags', help='Filter by tags (comma-separated)')
    parser.add_argument('--sprint', action='store_true', help='Show only sprint tasks')
    parser.add_argument('--all', action='store_true', help='Show all tasks including done/archived')
    parser.add_argument('--show-all', dest='all', action='store_true', help=argparse.SUPPRESS)

    # Sorting
    parser.add_argument('--sort',
                       choices=['priority', 'status', 'sp', 'created', 'updated', 'id', 'epic'],
                       default='priority',
                       help='Sort order')
    parser.add_argument('--format',
                       choices=['table', 'cards', 'ids', 'tsv'],
                       default='table',
                       help='Output format (table default)')
    parser.add_argument('--with', dest='columns', help='Comma-separated columns to display (no spaces, e.g., id,title,status,sp,tags)')

    return parser


def setup_show_parser(subparsers):
    """Setup argument parser for show command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for show command
    """
    parser = subparsers.add_parser(
        'show',
        help='Display task details'
    )

    parser.add_argument('task_ids', nargs='+', help='Task ID(s) to display')

    return parser


def setup_create_parser(subparsers):
    """Setup argument parser for create command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for create command
    """
    parser = subparsers.add_parser(
        'create',
        help='Create a new task'
    )

    parser.add_argument('epic', help='Epic name (e.g., BUGS, DOCS, FEAT)')
    parser.add_argument('title', nargs='+', help='Task title')

    parser.add_argument('--sp', '--story-points', dest='story_points', type=int, default=0,
                       help='Story points estimate')
    parser.add_argument('--priority', choices=['critical', 'high', 'medium', 'low'],
                       default='medium', help='Task priority')
    parser.add_argument('--status', choices=['stub', 'backlog', 'ready', 'active', 'qa', 'blocked'],
                       default='stub', help='Initial status (default: stub for incomplete tasks)')
    parser.add_argument('--tags', help='Comma-separated tags')
    parser.add_argument('--milestone', help='Assign to milestone (e.g., milestone-1)')
    parser.add_argument('--edit', action='store_true', help='Open task in editor after creation')
    parser.add_argument('--body', help='Task description body')
    parser.add_argument('--stub', action='store_true',
                       help='Mark as stub (skeletal ticket)')
    parser.add_argument('--auto', action='store_true',
                       help='When using manual IDs (EPIC-123), automatically bump to the next free ID if needed')

    return parser


def setup_edit_parser(subparsers):
    """Setup argument parser for edit command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for edit command
    """
    parser = subparsers.add_parser(
        'edit',
        help='Edit a task in $EDITOR'
    )

    parser.add_argument('task_id', help='Task ID to edit')

    return parser


def setup_rename_parser(subparsers):
    """Setup argument parser for rename command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for rename command
    """
    parser = subparsers.add_parser(
        'rename',
        help='Rename a task ID'
    )

    parser.add_argument('old_id', help='Current task ID')
    parser.add_argument('new_id', help='New task ID')
    parser.add_argument('--force', action='store_true', help='Overwrite existing task')
    parser.add_argument('--skip-manifest', action='store_true', help='Skip manifest rebuild')

    return parser


def setup_delete_parser(subparsers):
    """Setup parser for delete command."""
    parser = subparsers.add_parser(
        'delete',
        help='Move a task to trash (soft delete)'
    )
    parser.add_argument('task_id', help='Task ID to delete')
    parser.add_argument('--reason', required=True, help='Reason for deletion (logged in history)')
    return parser


def setup_trash_parser(subparsers):
    """Setup parser for trash command."""
    parser = subparsers.add_parser(
        'trash',
        help='View or empty the trash bin'
    )
    parser.add_argument('action', nargs='?', choices=['empty'],
                        help="Optional: 'empty' to permanently delete trashed tasks")
    return parser


def setup_recover_parser(subparsers):
    """Setup parser for recover command."""
    parser = subparsers.add_parser(
        'recover',
        help='Recover task from trash by auto_id'
    )
    parser.add_argument('auto_id', type=int, help='Auto ID of trashed task')
    parser.add_argument('--reason', required=True, help='Reason for recovery (logged in history)')
    return parser


__all__ = ['register']
