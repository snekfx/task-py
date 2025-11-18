"""
Modern CLI with feature registration system.

Access via: taskpy modern <command>
"""

import argparse
import sys

# Import all feature modules
from taskpy.modern import nfrs, epics, core, sprint, workflow


def build_cli():
    """Build CLI with all registered features.

    Returns:
        ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog='taskpy modern',
        description='Modern feature-based architecture (opt-in)'
    )

    # Add global flags to main parser
    parser.add_argument('--data', action='store_true', help='Plain data output')
    parser.add_argument('--agent', action='store_true', help='Agent-friendly output')
    parser.add_argument('--no-boxy', action='store_true', help='Disable boxy output')

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands'
    )

    # Register all feature modules
    features = [nfrs, epics, core, sprint, workflow]

    for feature in features:
        # Get command registrations from feature
        commands = feature.cli.register()

        for cmd_name, cmd_info in commands.items():
            # Setup parser for this command
            cmd_parser = cmd_info['parser'](subparsers)

            # Set the command function
            cmd_parser.set_defaults(func=cmd_info['func'])

    return parser


def main():
    """Main entry point for modern CLI."""
    parser = build_cli()

    # Parse arguments
    args = parser.parse_args()

    # If no command provided, show help
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    # Execute the command
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
