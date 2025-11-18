"""
Unit tests for modern views base module.

Tests the base View class and output mode handling.
"""

import pytest
from taskpy.modern.views.base import View
from taskpy.modern.views.output import OutputMode
from taskpy.legacy.output import OutputMode as LegacyOutputMode


class ConcreteView(View):
    """Concrete implementation of View for testing."""

    def render_pretty(self) -> str:
        return "PRETTY OUTPUT"

    def render_data(self) -> str:
        return "DATA OUTPUT"

    def render_agent(self) -> str:
        return "AGENT OUTPUT"


class TestView:
    """Test the base View class."""

    def test_view_defaults_to_pretty_mode(self):
        """Test that View defaults to PRETTY mode."""
        view = ConcreteView()
        assert view.output_mode == OutputMode.PRETTY

    def test_view_accepts_output_mode(self):
        """Test that View can be initialized with output mode."""
        view = ConcreteView(output_mode=OutputMode.DATA)
        assert view.output_mode == OutputMode.DATA

    def test_render_dispatches_to_pretty(self):
        """Test that render() dispatches to render_pretty() in PRETTY mode."""
        view = ConcreteView(output_mode=OutputMode.PRETTY)
        assert view.render() == "PRETTY OUTPUT"

    def test_render_dispatches_to_data(self):
        """Test that render() dispatches to render_data() in DATA mode."""
        view = ConcreteView(output_mode=OutputMode.DATA)
        assert view.render() == "DATA OUTPUT"

    def test_render_dispatches_to_agent(self):
        """Test that render() dispatches to render_agent() in AGENT mode."""
        view = ConcreteView(output_mode=OutputMode.AGENT)
        assert view.render() == "AGENT OUTPUT"

    def test_display_prints_output(self, capsys):
        """Test that display() prints rendered output."""
        view = ConcreteView(output_mode=OutputMode.PRETTY)
        view.display()

        captured = capsys.readouterr()
        assert "PRETTY OUTPUT" in captured.out

    def test_view_must_implement_abstract_methods(self):
        """Test that View cannot be instantiated without implementing abstract methods."""
        with pytest.raises(TypeError):
            # This should fail because View is abstract
            View()  # type: ignore

    def test_view_coerces_legacy_output_mode(self):
        """Legacy OutputMode enum should be coerced to the modern equivalent."""
        view = ConcreteView(output_mode=LegacyOutputMode.DATA)
        assert view.output_mode == OutputMode.DATA
        assert view.render() == "DATA OUTPUT"
