"""Lightweight message helpers for modern CLI output."""

from typing import Optional


def _emit(prefix: str, message: str, title: Optional[str] = None):
    if title:
        print(f"{prefix} {title}: {message}")
    else:
        print(f"{prefix} {message}")


def print_error(message: str, title: Optional[str] = None):
    _emit("[ERROR]", message, title)


def print_warning(message: str, title: Optional[str] = None):
    _emit("[WARN]", message, title)


def print_info(message: str, title: Optional[str] = None):
    _emit("[INFO]", message, title)


def print_success(message: str, title: Optional[str] = None):
    _emit("[OK]", message, title)
