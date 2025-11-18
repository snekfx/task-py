"""CLI registration for milestones management."""

import argparse
from .commands import cmd_milestones, cmd_milestone


def register():
    """Register milestones commands with main CLI.

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
        'milestones': {
            'func': cmd_milestones,
            'help': 'List all milestones',
            'parser': setup_milestones_parser
        },
        'milestone': {
            'func': cmd_milestone,
            'help': 'Manage milestone operations',
            'parser': setup_milestone_parser
        }
    }


def setup_milestones_parser(subparsers):
    """Setup argument parser for milestones command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for milestones command
    """
    parser = subparsers.add_parser(
        'milestones',
        help='List all milestones sorted by priority'
    )
    return parser


def setup_milestone_parser(subparsers):
    """Setup argument parser for milestone command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for milestone command
    """
    parser = subparsers.add_parser(
        'milestone',
        help='Manage milestone operations'
    )

    # Add subcommands
    milestone_subparsers = parser.add_subparsers(
        dest='milestone_command',
        help='Milestone subcommands'
    )

    # show subcommand
    show_parser = milestone_subparsers.add_parser(
        'show',
        help='Show milestone details and task statistics'
    )
    show_parser.add_argument('milestone_id', help='Milestone ID (e.g., M1, M2)')

    # start subcommand
    start_parser = milestone_subparsers.add_parser(
        'start',
        help='Mark milestone as active'
    )
    start_parser.add_argument('milestone_id', help='Milestone ID to start')

    # complete subcommand
    complete_parser = milestone_subparsers.add_parser(
        'complete',
        help='Mark milestone as completed'
    )
    complete_parser.add_argument('milestone_id', help='Milestone ID to complete')

    # assign subcommand
    assign_parser = milestone_subparsers.add_parser(
        'assign',
        help='Assign task to milestone'
    )
    assign_parser.add_argument('task_id', help='Task ID to assign')
    assign_parser.add_argument('milestone_id', help='Milestone ID to assign to')

    return parser


__all__ = ['register']
