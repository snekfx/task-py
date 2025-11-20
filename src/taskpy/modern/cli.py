"""
Modern CLI with feature registration system.

Access via: taskpy <command> (taskpy modern … is kept as an alias)
"""

import argparse
import sys

from taskpy.modern.shared.output import (
    set_output_mode as set_modern_output_mode,
    OutputMode as ModernOutputMode,
)
from taskpy.legacy.output import (
    set_output_mode as set_legacy_output_mode,
    OutputMode as LegacyOutputMode,
)

# Import all feature modules
from taskpy.modern import (
    nfrs,
    epics,
    core,
    sprint,
    workflow,
    display,
    admin,
    milestones,
    linking,
    blocking,
)

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
        prog='taskpy',
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
    features = [nfrs, epics, core, sprint, workflow, display, admin, milestones, linking, blocking]

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


def _configure_output_modes(args):
    """Configure legacy and modern output modes based on parsed args."""
    if getattr(args, 'agent', False):
        modern_mode = ModernOutputMode.AGENT
    elif getattr(args, 'data', False) or getattr(args, 'no_boxy', False):
        modern_mode = ModernOutputMode.DATA
    else:
        modern_mode = ModernOutputMode.PRETTY

    legacy_mode_map = {
        ModernOutputMode.PRETTY: LegacyOutputMode.PRETTY,
        ModernOutputMode.DATA: LegacyOutputMode.DATA,
        ModernOutputMode.AGENT: LegacyOutputMode.AGENT,
    }

    set_modern_output_mode(modern_mode)
    set_legacy_output_mode(legacy_mode_map[modern_mode])

    return modern_mode


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
    _configure_output_modes(args)

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
