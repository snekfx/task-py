"""
taskpy - File-based agile task management tool

A lightweight task management system that follows META PROCESS v3 patterns
with Kanban workflow, epic-based organization, and markdown task files.

Supports:
- Epic-based task organization (BUGS-NN, DOCS-NN, REF-NN, etc.)
- Kanban workflow with configurable states
- Story point estimation and tracking
- Reference linking (code, docs, NFRs, plans)
- Test verification integration
- TSV manifest for fast queries

Key features:
- File-based (no database required)
- Git-friendly (plain text, markdown)
- Self-documenting task files
- Integration with testpy and featpy
- Extensible for multi-language projects
"""

import sys
import importlib.metadata


def get_version() -> str:
    """
    Get version from package metadata.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        return importlib.metadata.version("taskpy")
    except importlib.metadata.PackageNotFoundError:
        # Fallback during development
        return "0.1.0-dev"


__version__ = get_version()
__author__ = "snekfx"

# Package metadata
__all__ = [
    "__version__",
    "__author__",
]
