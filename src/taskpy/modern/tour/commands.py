"""Command implementations for tour feature."""

from taskpy.legacy.help import TOUR_TEXT


def cmd_tour(args):
    """Display TaskPy quick reference tour."""
    print(TOUR_TEXT)


__all__ = ['cmd_tour']
