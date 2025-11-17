"""
Base View class for all modern view components.

Provides foundation for output mode handling and consistent rendering patterns.
"""

from abc import ABC, abstractmethod
from typing import Any
from taskpy.modern.views.output import OutputMode


class View(ABC):
    """
    Base class for all view components.

    All view subclasses must implement the render methods for different output modes.
    The base class handles mode detection and dispatching to the appropriate renderer.
    """

    def __init__(self, output_mode: OutputMode = OutputMode.PRETTY):
        """
        Initialize view with output mode.

        Args:
            output_mode: Output mode for rendering (PRETTY/DATA/AGENT)
        """
        self.output_mode = output_mode

    @abstractmethod
    def render_pretty(self) -> str:
        """
        Render in PRETTY mode (formatted, human-readable).

        Returns:
            Formatted string for terminal display
        """
        pass

    @abstractmethod
    def render_data(self) -> str:
        """
        Render in DATA mode (plain text, machine-parseable).

        Returns:
            Plain text string (TSV, CSV, or simple text)
        """
        pass

    @abstractmethod
    def render_agent(self) -> str:
        """
        Render in AGENT mode (structured, machine-readable).

        Returns:
            Structured string (JSON or other structured format)
        """
        pass

    def render(self) -> str:
        """
        Render view based on current output mode.

        Returns:
            Rendered output string
        """
        if self.output_mode == OutputMode.PRETTY:
            return self.render_pretty()
        elif self.output_mode == OutputMode.DATA:
            return self.render_data()
        elif self.output_mode == OutputMode.AGENT:
            return self.render_agent()
        else:
            # Default to pretty mode for unknown modes
            return self.render_pretty()

    def display(self):
        """
        Render and print view to stdout.
        """
        output = self.render()
        if output:
            print(output, end='')
