"""
ListView component - generalized list/table rendering.

Provides a reusable, data-agnostic list view that works with any tabular data
(tasks, epics, NFRs, milestones, etc.) with consistent styling and formatting.
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Callable, Dict
from taskpy.modern.views.base import View
from taskpy.modern.views.output import OutputMode, rolo_table, dim


# Status color mapping for consistent styling
STATUS_COLORS = {
    'stub': 'default',
    'backlog': 'default',
    'ready': 'cyan',
    'active': 'yellow',
    'qa': 'magenta',
    'done': 'dim',  # Grey out done tasks
}


@dataclass
class ColumnConfig:
    """Configuration for a table column."""
    name: str                              # Column header
    field: str | Callable                  # Attribute name or callable to get value
    width: Optional[int] = None            # Fixed width (None = auto)
    align: str = 'left'                    # Alignment: left, right, center
    formatter: Optional[Callable] = None   # Custom formatter function

    def get_value(self, obj: Any) -> str:
        """Extract value from object using field."""
        if callable(self.field):
            value = self.field(obj)
        elif hasattr(obj, self.field):
            value = getattr(obj, self.field)
        elif isinstance(obj, dict):
            value = obj.get(self.field, '')
        else:
            value = ''

        # Apply formatter if provided
        if self.formatter and value:
            value = self.formatter(value)

        return str(value) if value is not None else ''


class ListView(View):
    """
    Generalized list view for any tabular data.

    Works with tasks, epics, NFRs, or any list of objects/dicts.
    Supports column configuration, row styling, filtering, and sorting.
    """

    def __init__(
        self,
        data: List[Any],
        columns: List[ColumnConfig],
        title: Optional[str] = None,
        output_mode: OutputMode = OutputMode.PRETTY,
        status_field: Optional[str] = 'status',
        grey_done: bool = True,
    ):
        """
        Initialize ListView.

        Args:
            data: List of objects or dicts to display
            columns: Column configuration
            title: Optional title for the table
            output_mode: Output mode (PRETTY/DATA/AGENT)
            status_field: Field name for status (for styling), None to disable
            grey_done: Whether to grey out done/archived items
        """
        super().__init__(output_mode)
        self.data = data
        self.columns = columns
        self.title = title
        self.status_field = status_field
        self.grey_done = grey_done
        self._row_decorators: List[Callable] = []
        self._filters: List[Callable] = []
        self._sort_key: Optional[Callable] = None
        self._limit: Optional[int] = None

    def add_decorator(self, decorator: Callable) -> 'ListView':
        """
        Add a row decorator function.

        Decorator receives (row_data: List[str], obj: Any) and returns modified row_data.
        """
        self._row_decorators.append(decorator)
        return self

    def filter(self, predicate: Callable) -> 'ListView':
        """Add a filter predicate (returns True to include item)."""
        self._filters.append(predicate)
        return self

    def sort(self, key: Callable) -> 'ListView':
        """Set sort key function."""
        self._sort_key = key
        return self

    def limit(self, n: int) -> 'ListView':
        """Limit to first N items."""
        self._limit = n
        return self

    def _get_filtered_data(self) -> List[Any]:
        """Apply filters, sorting, and limit."""
        data = self.data

        # Apply filters
        for f in self._filters:
            data = [item for item in data if f(item)]

        # Apply sorting
        if self._sort_key:
            data = sorted(data, key=self._sort_key)

        # Apply limit
        if self._limit:
            data = data[:self._limit]

        return data

    def _get_status(self, obj: Any) -> Optional[str]:
        """Get status value from object for styling."""
        if not self.status_field:
            return None

        if hasattr(obj, self.status_field):
            status = getattr(obj, self.status_field)
        elif isinstance(obj, dict):
            status = obj.get(self.status_field)
        else:
            return None

        # Handle enum values
        if hasattr(status, 'value'):
            return status.value
        return str(status) if status else None

    def render_pretty(self) -> str:
        """Render as formatted table using rolo."""
        data = self._get_filtered_data()

        if not data:
            return f"\n{self.title or 'List'}\n{'-' * 20}\nNo items found.\n"

        # Build headers and rows
        headers = [col.name for col in self.columns]
        rows = []
        statuses = []

        for obj in data:
            # Extract values for each column
            row = [col.get_value(obj) for col in self.columns]

            # Apply decorators
            for decorator in self._row_decorators:
                row = decorator(row, obj)

            rows.append(row)

            # Track status for dimming
            status = self._get_status(obj)
            statuses.append(status)

        # Use rolo_table for pretty output
        rolo_table(
            headers=headers,
            rows=rows,
            title=self.title,
            row_statuses=statuses if self.grey_done else None,
            output_mode=self.output_mode,
        )

        return ""  # rolo_table prints directly

    def render_data(self) -> str:
        """Render as plain TSV for data mode."""
        data = self._get_filtered_data()

        if not data:
            return ""

        # Build TSV output
        lines = []

        # Header
        headers = [col.name for col in self.columns]
        lines.append("\t".join(headers))

        # Rows
        for obj in data:
            row = [col.get_value(obj) for col in self.columns]

            # Apply decorators
            for decorator in self._row_decorators:
                row = decorator(row, obj)

            lines.append("\t".join(row))

        output = "\n".join(lines)

        if self.title:
            output = f"{self.title}\n{output}"

        return output + "\n"

    def render_agent(self) -> str:
        """Render as JSON for agent mode."""
        import json

        data = self._get_filtered_data()

        if not data:
            return json.dumps({"items": [], "count": 0})

        # Build list of dicts
        items = []
        for obj in data:
            item = {}
            for col in self.columns:
                item[col.name] = col.get_value(obj)
            status = self._get_status(obj)
            if status:
                item["_status"] = status
            items.append(item)

        result = {
            "items": items,
            "count": len(items),
        }

        if self.title:
            result["title"] = self.title
        if self.status_field:
            result["status_field"] = self.status_field

        return json.dumps(result, indent=2) + "\n"
