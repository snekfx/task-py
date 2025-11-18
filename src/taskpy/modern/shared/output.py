"""Modern output mode state management."""

from enum import Enum


class OutputMode(Enum):
    """Output mode selection for modern modules."""
    PRETTY = "pretty"
    DATA = "data"
    AGENT = "agent"


_OUTPUT_MODE = OutputMode.PRETTY


def set_output_mode(mode: OutputMode):
    """Set the current output mode for modern commands."""
    global _OUTPUT_MODE
    _OUTPUT_MODE = mode


def get_output_mode() -> OutputMode:
    """Retrieve the currently configured output mode."""
    return _OUTPUT_MODE
