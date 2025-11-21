"""Feature flag command implementations."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Dict

from taskpy.legacy.output import print_error, print_info, print_success
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.shared.config import load_feature_flags, set_feature_flag
from taskpy.modern.shared.utils import require_initialized

SUPPORTED_FLAGS: Dict[str, str] = {
    "strict_mode": "Require gated workflow steps; block overrides and forced QA/DONE moves.",
    "signoff_mode": "Require explicit signoff list for archiving done tasks.",
}


def _normalize_flag(name: str) -> str:
    return name.replace("-", "_").lower()


def _print_available_flags():
    print_info("Available feature flags:")
    for flag, desc in SUPPORTED_FLAGS.items():
        print(f"  • {flag}: {desc}")


def _assert_supported(flag_name: str):
    if flag_name not in SUPPORTED_FLAGS:
        print_error(f"Unknown flag: {flag_name}")
        _print_available_flags()
        raise SystemExit(1)


def _update_flag(flag_name: str, enabled: bool, root: Path):
    flags = set_feature_flag(flag_name, enabled, root)
    status = "enabled" if enabled else "disabled"
    print_success(f"{flag_name} {status}", "Feature Flag Updated")
    return flags


def cmd_flag(args: Namespace):
    """Entry point for `taskpy flag` commands."""
    storage = TaskStorage(Path.cwd())
    require_initialized(storage)

    action = getattr(args, "flag_action", "list")

    if action == "list":
        flags = load_feature_flags(storage.root)
        if not flags:
            print_info("No feature flags set in config.toml")
        else:
            print_success("Feature flag status", "Flags")
            for name, enabled in sorted(flags.items()):
                status = "on" if enabled else "off"
                print(f"  • {name}: {status}")
        _print_available_flags()
        return

    flag_name = _normalize_flag(getattr(args, "flag_name", ""))
    _assert_supported(flag_name)

    if action == "enable":
        _update_flag(flag_name, True, storage.root)
    elif action == "disable":
        _update_flag(flag_name, False, storage.root)
    else:  # pragma: no cover - parser should prevent this
        print_error(f"Unknown flag action: {action}")
        raise SystemExit(1)


__all__ = ["cmd_flag"]
