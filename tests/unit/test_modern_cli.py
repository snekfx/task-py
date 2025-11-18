"""Unit tests for the modern CLI helpers."""

from types import SimpleNamespace
from unittest.mock import patch

from taskpy.modern.cli import (
    _configure_output_modes,
    ModernOutputMode,
    LegacyOutputMode,
)


def _args(agent=False, data=False, no_boxy=False):
    return SimpleNamespace(agent=agent, data=data, no_boxy=no_boxy)


@patch('taskpy.modern.cli.set_legacy_output_mode')
@patch('taskpy.modern.cli.set_modern_output_mode')
def test_configure_output_modes_agent(modern_mode_mock, legacy_mode_mock):
    """Agent flag should select AGENT mode for both systems."""
    _configure_output_modes(_args(agent=True))

    modern_mode_mock.assert_called_once_with(ModernOutputMode.AGENT)
    legacy_mode_mock.assert_called_once_with(LegacyOutputMode.AGENT)


@patch('taskpy.modern.cli.set_legacy_output_mode')
@patch('taskpy.modern.cli.set_modern_output_mode')
def test_configure_output_modes_data(modern_mode_mock, legacy_mode_mock):
    """Data flag should force DATA mode with plain output."""
    _configure_output_modes(_args(data=True))

    modern_mode_mock.assert_called_once_with(ModernOutputMode.DATA)
    legacy_mode_mock.assert_called_once_with(LegacyOutputMode.DATA)


@patch('taskpy.modern.cli.set_legacy_output_mode')
@patch('taskpy.modern.cli.set_modern_output_mode')
def test_configure_output_modes_no_boxy(modern_mode_mock, legacy_mode_mock):
    """--no-boxy is treated as DATA mode for consistent behavior."""
    _configure_output_modes(_args(no_boxy=True))

    modern_mode_mock.assert_called_once_with(ModernOutputMode.DATA)
    legacy_mode_mock.assert_called_once_with(LegacyOutputMode.DATA)


@patch('taskpy.modern.cli.set_legacy_output_mode')
@patch('taskpy.modern.cli.set_modern_output_mode')
def test_configure_output_modes_default_pretty(modern_mode_mock, legacy_mode_mock):
    """No flags should fall back to PRETTY mode."""
    _configure_output_modes(_args())

    modern_mode_mock.assert_called_once_with(ModernOutputMode.PRETTY)
    legacy_mode_mock.assert_called_once_with(LegacyOutputMode.PRETTY)
