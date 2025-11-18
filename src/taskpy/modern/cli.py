"""
Modern CLI with feature registration system.

Access via: taskpy modern <command>
"""

import argparse
import sys

from taskpy.modern.shared.output import set_output_mode, OutputMode

# Import all feature modules
from taskpy.modern import nfrs, epics, core, sprint, workflow, display, admin, milestones

GLOBAL_FLAG_MAP = {
    '--data': 'data',
    '--agent': 'agent',
    '--no-boxy': 'no_boxy',
}


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
    features = [nfrs, epics, core, sprint, workflow, display, admin, milestones]

    for feature in features:
        # Get command registrations from feature
        commands = feature.cli.register()

        for cmd_name, cmd_info in commands.items():
            # Setup parser for this command
            cmd_parser = cmd_info['parser'](subparsers)

            # Set the command function
            cmd_parser.set_defaults(func=cmd_info['func'])

    return parser


def _extract_global_flags(argv):
    """Allow global flags to be specified anywhere in the command."""
    flags = {name: False for name in GLOBAL_FLAG_MAP.values()}
    remaining = []

    for token in argv:
        flag_name = GLOBAL_FLAG_MAP.get(token)
        if flag_name:
            flags[flag_name] = True
            continue
        remaining.append(token)

    return flags, remaining


def main(argv=None):
    """Main entry point for modern CLI."""
    if argv is None:
        argv = sys.argv[1:]

    flag_values, remaining = _extract_global_flags(argv)

    parser = build_cli()

    # Parse arguments
    args = parser.parse_args(remaining)

    # Merge extracted flag values so downstream handlers can introspect them
    for attr, value in flag_values.items():
        setattr(args, attr, getattr(args, attr, False) or value)

    # Configure global output mode for downstream modules
    if getattr(args, 'agent', False):
        set_output_mode(OutputMode.AGENT)
    elif getattr(args, 'data', False) or getattr(args, 'no_boxy', False):
        set_output_mode(OutputMode.DATA)
    else:
        set_output_mode(OutputMode.PRETTY)

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
