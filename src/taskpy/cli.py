"""
CLI entry point - routes to legacy or modern implementation.

This module provides backward compatibility for the entry point script
while routing to the appropriate implementation.
"""

from taskpy.legacy.cli import main

__all__ = ['main']
