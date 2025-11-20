"""
CLI entry point - defaults to modern implementation.

If users invoke `taskpy modern ...` we drop the alias for backward
compatibility. `taskpy legacy ...` is kept temporarily for anyone who
still needs the old CLI surface.
"""

from __future__ import annotations

import sys
from pathlib import Path

from taskpy import __version__
from taskpy.modern import cli as modern_cli

VERSION_FLAGS = {"-v", "--version"}


def _view_flag(value: str | None) -> str | None:
    if not value:
        return None
    value = value.lower()
    if value == "data":
        return "--data"
    if value == "agent":
        return "--agent"
    if value == "pretty":
        return None
    return None


def _normalize_legacy_flags(args: list[str]) -> list[str]:
    """Map legacy global flags to modern equivalents."""
    normalized: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--show-all":
            normalized.append("--all")
            i += 1
            continue
        if token == "--view":
            if i + 1 >= len(args):
                normalized.append(token)
                break
            replacement = _view_flag(args[i + 1])
            if replacement:
                normalized.append(replacement)
            i += 2
            continue
        if token.startswith("--view="):
            replacement = _view_flag(token.split("=", 1)[1])
            if replacement:
                normalized.append(replacement)
            i += 1
            continue
        normalized.append(token)
        i += 1
    return normalized


def _print_version():
    """Display logo + version info."""
    logo_path = Path(__file__).parent / "logo.txt"
    try:
        logo = logo_path.read_text().rstrip()
        if logo:
            print(logo)
    except OSError:
        pass

    print(f"Version: {__version__} | License: AGPLv3")
    print("Copyright © 2025 Qodeninja/SnekFX")


def main(argv: list[str] | None = None):
    """Route to the modern CLI (with legacy shims)."""
    if argv is None:
        argv = sys.argv[1:]

    if any(flag in argv for flag in VERSION_FLAGS):
        _print_version()
        return

    args = _normalize_legacy_flags(list(argv))

    if args and args[0] == "modern":
        print("`taskpy modern …` has been removed. Use `taskpy …` directly.", file=sys.stderr)
        sys.exit(2)

    modern_cli.main(args)


__all__ = ["main"]
