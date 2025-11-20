"""Test fixtures shared across modern unit tests."""

import pytest

from taskpy.modern.shared.output import set_output_mode, OutputMode


@pytest.fixture(autouse=True)
def reset_output_mode():
    """Ensure each test starts (and ends) in PRETTY output mode."""
    set_output_mode(OutputMode.PRETTY)
    yield
    set_output_mode(OutputMode.PRETTY)
