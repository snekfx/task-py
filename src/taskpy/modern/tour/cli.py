"""CLI registration for tour feature."""

from .commands import cmd_tour


def register():
    """Register tour command with main CLI.

    Returns:
        dict: Command registration info
    """
    return {
        'tour': {
            'func': cmd_tour,
            'help': 'Display TaskPy quick reference guide',
            'parser': setup_parser
        }
    }


def setup_parser(subparsers):
    """Setup argument parser for tour command.

    Args:
        subparsers: argparse subparsers object

    Returns:
        ArgumentParser: Configured parser for tour command
    """
    parser = subparsers.add_parser(
        'tour',
        help='Display TaskPy quick reference guide'
    )

    return parser
