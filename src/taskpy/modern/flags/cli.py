"""CLI registration for feature flag management."""

import argparse
from .commands import cmd_flag


def register():
    """Register flag command with main CLI."""
    return {
        'flag': {
            'func': cmd_flag,
            'help': 'Manage feature flags',
            'parser': setup_flag_parser,
        }
    }


def setup_flag_parser(subparsers: argparse._SubParsersAction):
    parser = subparsers.add_parser(
        'flag',
        help='Enable, disable, or list feature flags',
    )
    parser.set_defaults(flag_action='list')

    flag_subparsers = parser.add_subparsers(dest='flag_action', help='Flag actions')

    enable_parser = flag_subparsers.add_parser('enable', help='Enable a feature flag')
    enable_parser.add_argument('flag_name', help='Flag name to enable')

    disable_parser = flag_subparsers.add_parser('disable', help='Disable a feature flag')
    disable_parser.add_argument('flag_name', help='Flag name to disable')

    flag_subparsers.add_parser('list', help='List configured feature flags')

    return parser


__all__ = ['register']
