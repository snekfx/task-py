"""
Modern views module for reusable display components.

This module provides generalized, reusable view components for rendering
tasks, epics, NFRs, and other data in consistent, customizable formats.

Key components:
- View: Base class with output mode support (PRETTY/DATA/AGENT)
- ListView: Generalized list/table view for any tabular data
- BoxView: Customizable box/card displays
- Layout components: Header, Footer, StatusBar, Separator

All views automatically handle --data and --agent flags for alternative
output formats.
"""

__version__ = "0.1.0"

# Import order matters for circular dependencies
from taskpy.modern.views.base import View
from taskpy.modern.views.output import (
    OutputMode,
    Theme,
    has_boxy,
    has_rolo,
    rolo_table,
    show_card,
    show_column,
)

__all__ = [
    'View',
    'OutputMode',
    'Theme',
    'has_boxy',
    'has_rolo',
    'rolo_table',
    'show_card',
    'show_column',
]
