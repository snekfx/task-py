"""Helpers for reading and updating TaskPy configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for 3.10
    import tomli as tomllib

CONFIG_FILENAME = "config.toml"
FEATURES_SECTION = "features"
SIGNOFF_SECTION = "signoff"
SIGNOFF_KEY = "tickets"


def _config_path(root: Optional[Path] = None) -> Path:
    base = Path.cwd() if root is None else root
    return base / "data" / "kanban" / "info" / CONFIG_FILENAME


def load_config(root: Optional[Path] = None) -> Dict[str, object]:
    """Load config.toml into a dictionary, returning empty dict if missing."""
    path = _config_path(root)
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_feature_flags(root: Optional[Path] = None) -> Dict[str, bool]:
    """Return feature flags dictionary (empty if not configured)."""
    config = load_config(root)
    features = config.get(FEATURES_SECTION, {}) if isinstance(config, dict) else {}
    return {name: bool(value) for name, value in features.items()}


def is_feature_enabled(flag_name: str, root: Optional[Path] = None) -> bool:
    """Check whether a named feature flag is enabled."""
    normalized = flag_name.replace("-", "_").lower()
    features = load_feature_flags(root)
    return bool(features.get(normalized, False))


def _render_features(flags: Dict[str, bool]) -> str:
    lines = [f"[{FEATURES_SECTION}]"]
    for name, value in sorted(flags.items()):
        lines.append(f"{name} = {str(bool(value)).lower()}")
    return "\n".join(lines) + "\n"


def _render_signoff(tickets: list[str]) -> str:
    ticket_list = ", ".join(f'"{t}"' for t in sorted({t.upper() for t in tickets}))
    return f"[{SIGNOFF_SECTION}]\n{SIGNOFF_KEY} = [{ticket_list}]\n"


def _replace_section(config_text: str, section: str, rendered: str) -> str:
    """Replace (or append) a TOML section with rendered content."""
    lines = config_text.splitlines()
    output: list[str] = []
    in_section = False
    wrote_section = False
    section_header = f"[{section}]"

    for line in lines:
        stripped = line.strip()
        is_section_header = stripped.startswith("[") and stripped.endswith("]")
        if is_section_header:
            if stripped == "[features]":
                # normalize legacy feature header to constant
                stripped = section_header if section == FEATURES_SECTION else stripped
            if stripped == section_header:
                if not wrote_section:
                    output.append(rendered.rstrip("\n"))
                    wrote_section = True
                in_section = True
                continue  # Skip original header and section content
            else:
                if in_section:
                    in_section = False
        if in_section:
            # Skip old section lines until we leave the section
            continue
        output.append(line)

    if not wrote_section:
        if output and output[-1].strip():
            output.append("")
        output.append(rendered.rstrip("\n"))

    return "\n".join(output) + "\n"


def set_feature_flag(flag_name: str, enabled: bool, root: Optional[Path] = None) -> Dict[str, bool]:
    """Persist a feature flag in config.toml and return the updated flags."""
    normalized = flag_name.replace("-", "_").lower()
    path = _config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_text = path.read_text() if path.exists() else ""
    flags = load_feature_flags(root)
    flags[normalized] = bool(enabled)

    rendered = _render_features(flags)
    updated_text = _replace_section(existing_text, FEATURES_SECTION, rendered)
    path.write_text(updated_text)

    return flags


def load_signoff_list(root: Optional[Path] = None) -> list[str]:
    """Return configured signoff tickets (uppercase)."""
    config = load_config(root)
    section = config.get(SIGNOFF_SECTION, {}) if isinstance(config, dict) else {}
    tickets = section.get(SIGNOFF_KEY, []) if isinstance(section, dict) else []
    return [t.strip().upper() for t in tickets if isinstance(t, str) and t.strip()]


def set_signoff_list(tickets: list[str], root: Optional[Path] = None) -> list[str]:
    """Persist the signoff ticket list in config.toml and return the updated list."""
    normalized = [t.strip().upper() for t in tickets if t.strip()]
    path = _config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_text = path.read_text() if path.exists() else ""
    rendered = _render_signoff(normalized)
    updated_text = _replace_section(existing_text, SIGNOFF_SECTION, rendered)
    path.write_text(updated_text)
    return normalized


def add_signoff_tickets(tickets: list[str], root: Optional[Path] = None) -> list[str]:
    """Add tickets to the signoff list and persist."""
    current = set(load_signoff_list(root))
    current.update(t.strip().upper() for t in tickets if t.strip())
    return set_signoff_list(sorted(current), root)


def remove_signoff_tickets(tickets: list[str], root: Optional[Path] = None) -> list[str]:
    """Remove tickets from the signoff list and persist."""
    remove_set = {t.strip().upper() for t in tickets if t.strip()}
    current = [t for t in load_signoff_list(root) if t not in remove_set]
    return set_signoff_list(current, root)


__all__ = [
    "is_feature_enabled",
    "load_config",
    "load_feature_flags",
    "set_feature_flag",
    "load_signoff_list",
    "set_signoff_list",
    "add_signoff_tickets",
    "remove_signoff_tickets",
]
