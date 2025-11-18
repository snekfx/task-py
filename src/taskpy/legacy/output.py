"""
Output and display system for TaskPy.

Provides boxy/rolo integration for pretty terminal output with graceful fallback.
Supports ergonomic human views (task cards, kanban boards, tables) and
machine-readable data output.
"""

import os
import shutil
import subprocess
import sys
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path


class OutputMode(Enum):
    """Output mode selection."""
    PRETTY = "pretty"  # Use boxy/rolo if available
    DATA = "data"      # Plain text, no formatting (for scripting/AI)


class Theme(Enum):
    """Boxy themes for different message types."""
    SUCCESS = "success"   # Green, for completed tasks
    WARNING = "warning"   # Yellow, for blocked/at-risk tasks
    ERROR = "error"       # Red, for errors
    INFO = "info"         # Blue, for informational messages
    MAGIC = "magic"       # Purple, for special displays
    TASK = "task"         # Task card theme
    PLAIN = "plain"       # No special formatting


# Global settings
_OUTPUT_MODE = OutputMode.PRETTY
_BOXY_AVAILABLE = None
_ROLO_AVAILABLE = None
_TABLE_WIDTH = None


def check_boxy_availability() -> bool:
    """
    Check if boxy is available and working.

    Returns:
        True if boxy is available, False otherwise
    """
    global _BOXY_AVAILABLE

    if _BOXY_AVAILABLE is not None:
        return _BOXY_AVAILABLE

    # Check REPOS_USE_BOXY environment variable (1=disabled, 0=enabled)
    if os.getenv("REPOS_USE_BOXY") == "1":
        _BOXY_AVAILABLE = False
        return False

    boxy_path = shutil.which("boxy")
    if not boxy_path:
        _BOXY_AVAILABLE = False
        return False

    try:
        result = subprocess.run(
            [boxy_path, "--version"],
            capture_output=True,
            timeout=2,
            text=True
        )
        _BOXY_AVAILABLE = result.returncode == 0
        return _BOXY_AVAILABLE
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        _BOXY_AVAILABLE = False
        return False


def check_rolo_availability() -> bool:
    """
    Check if rolo is available and working.

    Returns:
        True if rolo is available, False otherwise
    """
    global _ROLO_AVAILABLE

    if _ROLO_AVAILABLE is not None:
        return _ROLO_AVAILABLE

    rolo_path = shutil.which("rolo")
    if not rolo_path:
        _ROLO_AVAILABLE = False
        return False

    try:
        result = subprocess.run(
            [rolo_path, "--version"],
            capture_output=True,
            timeout=2,
            text=True
        )
        _ROLO_AVAILABLE = result.returncode == 0
        return _ROLO_AVAILABLE
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        _ROLO_AVAILABLE = False
        return False


def set_output_mode(mode: OutputMode):
    """Set global output mode."""
    global _OUTPUT_MODE
    _OUTPUT_MODE = mode


def get_output_mode() -> OutputMode:
    """Get current output mode."""
    return _OUTPUT_MODE


def boxy_display(
    content: str,
    theme: Theme = Theme.PLAIN,
    title: Optional[str] = None,
    width: str = "max",
) -> bool:
    """
    Display content using boxy with fallback to plain output.

    Args:
        content: Content to display
        theme: Boxy theme to use
        title: Optional title for the box
        width: Box width ("max", "80", "100", etc.)

    Returns:
        True if displayed via boxy, False if fallback used
    """
    if _OUTPUT_MODE == OutputMode.DATA:
        _plain_output(content, theme.value, title)
        return False

    if not check_boxy_availability():
        _plain_output(content, theme.value, title)
        return False

    cmd = ["boxy"]

    if theme != Theme.PLAIN:
        cmd.extend(["--theme", theme.value])

    if title:
        cleaned_title = title.lstrip()
        while cleaned_title and not cleaned_title[0].isalnum():
            cleaned_title = cleaned_title[1:].lstrip()
        if not cleaned_title:
            cleaned_title = title.strip()
        cmd.extend(["--title", cleaned_title])

    if width:
        cmd.extend(["--width", width])

    try:
        result = subprocess.run(
            cmd,
            input=content,
            text=True,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(result.stdout, end="")
            return True
        else:
            _plain_output(content, theme.value, title)
            return False

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        _plain_output(content, theme.value, title)
        return False


def rolo_table(
    headers: List[str],
    rows: List[List[str]],
    title: Optional[str] = None,
    row_statuses: Optional[List[str]] = None,
) -> bool:
    """
    Display tabular data using rolo with fallback to plain text.

    Args:
        headers: Column headers
        rows: Data rows
        title: Optional title
        row_statuses: Optional list of row statuses for dimming done/archived rows

    Returns:
        True if displayed via rolo, False if fallback used
    """
    if _OUTPUT_MODE == OutputMode.DATA:
        _plain_table(headers, rows, title, row_statuses)
        return False

    if not check_rolo_availability():
        _plain_table(headers, rows, title, row_statuses)
        return False

    # Build TSV input for rolo with dimming for done/archived rows
    tsv_lines = []
    tsv_lines.append("\t".join(headers))
    for row_idx, row in enumerate(rows):
        # Apply dimming to done/archived rows
        status = row_statuses[row_idx] if row_statuses and row_idx < len(row_statuses) else None
        if status in ['done', 'archived']:
            # Apply dim styling to each cell
            dimmed_row = [dim(str(cell)) for cell in row]
            tsv_lines.append("\t".join(dimmed_row))
        else:
            tsv_lines.append("\t".join(str(cell) for cell in row))

    tsv_input = "\n".join(tsv_lines)

    def _get_table_width() -> int:
        """Determine desired table width with env override."""
        global _TABLE_WIDTH
        if _TABLE_WIDTH is not None:
            return _TABLE_WIDTH

        env_width = os.getenv("TASKPY_TABLE_WIDTH")
        if env_width:
            try:
                _TABLE_WIDTH = max(80, int(env_width))
                return _TABLE_WIDTH
            except ValueError:
                pass

        term_width = shutil.get_terminal_size(fallback=(120, 40)).columns
        _TABLE_WIDTH = max(140, term_width)
        return _TABLE_WIDTH

    try:
        result = subprocess.run(
            ["rolo", "table", "--border=unicode", f"--width={_get_table_width()}"],
            input=tsv_input,
            text=True,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            if title:
                print(f"\n{title}")
                print("-" * len(title))
            print(result.stdout)
            return True
        else:
            _plain_table(headers, rows, title, row_statuses)
            return False

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        _plain_table(headers, rows, title, row_statuses)
        return False


def dim(text: str) -> str:
    """Apply ANSI dim styling to text."""
    return f"\033[2m{text}\033[0m"


def _plain_output(content: str, theme: str, title: Optional[str]):
    """Fallback plain text output."""
    if title:
        print(f"=== {title} ===")
    print(content)
    if title:
        print("=" * (len(title) + 8))


def _plain_table(headers: List[str], rows: List[List[str]], title: Optional[str], row_statuses: Optional[List[str]] = None):
    """Fallback plain text table."""
    if title:
        print(f"\n{title}")
        print("-" * len(title))

    # Calculate column widths (without ANSI codes)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Print rows with dimming for done/archived
    for row_idx, row in enumerate(rows):
        status = row_statuses[row_idx] if row_statuses and row_idx < len(row_statuses) else None
        if status in ['done', 'archived']:
            # Dim content first, then pad with extra space for ANSI codes (8 chars: \033[2m + \033[0m)
            cells = []
            for i, cell in enumerate(row):
                dimmed = dim(str(cell))
                # Pad to col_width + 8 to account for invisible ANSI codes
                padded = dimmed + ' ' * (col_widths[i] - len(str(cell)))
                cells.append(padded)
            row_line = " | ".join(cells)
        else:
            row_line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(row_line)

    print()


def print_success(message: str, title: Optional[str] = None):
    """Print success message."""
    boxy_display(message, Theme.SUCCESS, title or "✓ Success")


def print_warning(message: str, title: Optional[str] = None):
    """Print warning message."""
    boxy_display(message, Theme.WARNING, title or "⚠ Warning")


def print_error(message: str, title: Optional[str] = None):
    """Print error message."""
    boxy_display(message, Theme.ERROR, title or "✗ Error")


def print_info(message: str, title: Optional[str] = None):
    """Print informational message."""
    boxy_display(message, Theme.INFO, title or "ℹ Info")


def format_task_card(task_data: Dict[str, Any]) -> str:
    """
    Format a task as a card for display.

    Args:
        task_data: Task data dictionary

    Returns:
        Formatted task card string
    """
    lines = []
    lines.append(f"ID: {task_data['id']}")
    lines.append(f"Title: {task_data['title']}")
    lines.append(f"Status: {task_data['status']} | Priority: {task_data.get('priority', 'medium')}")
    lines.append(f"Story Points: {task_data.get('story_points', 0)}")

    if task_data.get('tags'):
        lines.append(f"Tags: {', '.join(task_data['tags'])}")

    if task_data.get('dependencies'):
        lines.append(f"Depends on: {', '.join(task_data['dependencies'])}")

    if task_data.get('assigned'):
        lines.append(f"Assigned: {task_data['assigned']}")

    if task_data.get('references'):
        lines.append("")
        lines.append("References:")
        lines.append(task_data['references'])

    lines.append("")
    lines.append(task_data.get('content', '').strip())

    return "\n".join(lines)


def display_task_card(task_data: Dict[str, Any]):
    """Display a task as a pretty card."""
    card = format_task_card(task_data)
    status = task_data.get('status', 'backlog')

    # Choose theme based on status
    theme_map = {
        'done': Theme.SUCCESS,
        'active': Theme.INFO,
        'qa': Theme.INFO,
        'regression': Theme.WARNING,
        'blocked': Theme.WARNING,
        'backlog': Theme.PLAIN,
    }
    theme = theme_map.get(status, Theme.PLAIN)

    boxy_display(card, theme, f"Task: {task_data['id']}")


def display_kanban_column(column_name: str, tasks: List[Dict[str, Any]]):
    """Display a Kanban column with tasks."""
    lines = [f"{column_name.upper()} ({len(tasks)} tasks)"]
    lines.append("=" * 40)

    for task in tasks:
        # Add sprint badge for sprint tasks
        sprint_badge = "🏃 " if task.get('in_sprint', 'false') == 'true' else ""
        lines.append(f"  • {sprint_badge}{task['id']}: {task['title']} [{task.get('story_points', 0)} SP]")

    content = "\n".join(lines)
    boxy_display(content, Theme.INFO, column_name.replace("_", " ").title())
