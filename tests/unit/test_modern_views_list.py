"""
Unit tests for modern views ListView component.

Tests the generalized list view with column config, filtering, sorting, and styling.
"""

import pytest
import json
from taskpy.modern.views.list import ListView, ColumnConfig
from taskpy.modern.views.output import OutputMode


class TestColumnConfig:
    """Test ColumnConfig dataclass."""

    def test_column_config_basics(self):
        """Test basic column configuration."""
        col = ColumnConfig(name="ID", field="id")
        assert col.name == "ID"
        assert col.field == "id"
        assert col.align == "left"
        assert col.formatter is None

    def test_get_value_from_dict(self):
        """Test extracting value from dictionary."""
        col = ColumnConfig(name="Name", field="name")
        obj = {"name": "Test", "other": "value"}
        assert col.get_value(obj) == "Test"

    def test_get_value_from_object(self):
        """Test extracting value from object with attributes."""
        class Task:
            def __init__(self):
                self.id = "TASK-1"
                self.title = "Test"

        col = ColumnConfig(name="ID", field="id")
        task = Task()
        assert col.get_value(task) == "TASK-1"

    def test_get_value_with_callable(self):
        """Test using callable as field."""
        col = ColumnConfig(name="Upper", field=lambda x: x['name'].upper())
        obj = {"name": "test"}
        assert col.get_value(obj) == "TEST"

    def test_get_value_with_formatter(self):
        """Test applying formatter to value."""
        col = ColumnConfig(
            name="Points",
            field="points",
            formatter=lambda x: f"{x} SP"
        )
        obj = {"points": 5}
        assert col.get_value(obj) == "5 SP"

    def test_get_value_missing_field(self):
        """Test handling missing field."""
        col = ColumnConfig(name="Missing", field="nonexistent")
        obj = {"name": "test"}
        assert col.get_value(obj) == ""


class TestListView:
    """Test ListView component."""

    def test_listview_creation(self):
        """Test creating a ListView."""
        data = [{"id": "1", "name": "Test"}]
        columns = [ColumnConfig(name="ID", field="id")]
        view = ListView(data, columns)
        assert len(view.data) == 1
        assert len(view.columns) == 1

    def test_listview_filter(self):
        """Test filtering data."""
        data = [
            {"id": "1", "status": "active"},
            {"id": "2", "status": "done"},
            {"id": "3", "status": "active"},
        ]
        columns = [ColumnConfig(name="ID", field="id")]
        view = ListView(data, columns)
        view.filter(lambda x: x['status'] == 'active')

        filtered = view._get_filtered_data()
        assert len(filtered) == 2
        assert filtered[0]['id'] == "1"
        assert filtered[1]['id'] == "3"

    def test_listview_sort(self):
        """Test sorting data."""
        data = [
            {"id": "3", "priority": "low"},
            {"id": "1", "priority": "high"},
            {"id": "2", "priority": "medium"},
        ]
        columns = [ColumnConfig(name="ID", field="id")]
        view = ListView(data, columns)
        view.sort(key=lambda x: x['id'])

        sorted_data = view._get_filtered_data()
        assert sorted_data[0]['id'] == "1"
        assert sorted_data[1]['id'] == "2"
        assert sorted_data[2]['id'] == "3"

    def test_listview_limit(self):
        """Test limiting results."""
        data = [{"id": str(i)} for i in range(10)]
        columns = [ColumnConfig(name="ID", field="id")]
        view = ListView(data, columns)
        view.limit(3)

        limited = view._get_filtered_data()
        assert len(limited) == 3

    def test_listview_chaining(self):
        """Test method chaining."""
        data = [
            {"id": "1", "status": "active", "priority": 3},
            {"id": "2", "status": "done", "priority": 1},
            {"id": "3", "status": "active", "priority": 2},
            {"id": "4", "status": "active", "priority": 1},
        ]
        columns = [ColumnConfig(name="ID", field="id")]

        view = ListView(data, columns)
        result = (view
                  .filter(lambda x: x['status'] == 'active')
                  .sort(key=lambda x: x['priority'])
                  .limit(2)
                  ._get_filtered_data())

        assert len(result) == 2
        assert result[0]['priority'] == 1  # Lowest priority first
        assert result[1]['priority'] == 2


class TestListViewRendering:
    """Test ListView render methods."""

    def test_render_data_mode(self):
        """Test rendering in DATA mode (TSV)."""
        data = [
            {"id": "TASK-1", "title": "First", "status": "active"},
            {"id": "TASK-2", "title": "Second", "status": "done"},
        ]
        columns = [
            ColumnConfig(name="ID", field="id"),
            ColumnConfig(name="Title", field="title"),
        ]

        view = ListView(data, columns, output_mode=OutputMode.DATA)
        output = view.render_data()

        assert "ID\tTitle" in output
        assert "TASK-1\tFirst" in output
        assert "TASK-2\tSecond" in output

    def test_render_agent_mode(self):
        """Test rendering in AGENT mode (JSON)."""
        data = [
            {"id": "TASK-1", "title": "First", "status": "active"},
            {"id": "TASK-2", "title": "Second", "status": "done"},
        ]
        columns = [
            ColumnConfig(name="ID", field="id"),
            ColumnConfig(name="Title", field="title"),
        ]

        view = ListView(
            data,
            columns,
            title="Tasks",
            output_mode=OutputMode.AGENT,
            status_field='status',
        )
        output = view.render_agent()

        parsed = json.loads(output)
        assert parsed["count"] == 2
        assert parsed["title"] == "Tasks"
        assert len(parsed["items"]) == 2
        assert parsed["items"][0]["ID"] == "TASK-1"
        assert parsed["items"][0]["Title"] == "First"
        assert parsed["items"][0]["_status"] == "active"
        assert parsed["status_field"] == "status"

    def test_render_empty_data(self):
        """Test rendering with no data."""
        data = []
        columns = [ColumnConfig(name="ID", field="id")]

        view = ListView(data, columns, output_mode=OutputMode.DATA)
        output = view.render_data()
        assert output == ""

        view_agent = ListView(data, columns, output_mode=OutputMode.AGENT)
        output_agent = view_agent.render_agent()
        parsed = json.loads(output_agent)
        assert parsed["count"] == 0
        assert parsed["items"] == []


class TestListViewDecorators:
    """Test row decorator functionality."""

    def test_add_decorator(self):
        """Test adding row decorator."""
        data = [{"id": "1", "value": "test"}]
        columns = [
            ColumnConfig(name="ID", field="id"),
            ColumnConfig(name="Value", field="value"),
        ]

        def uppercase_decorator(row, obj):
            """Make all values uppercase."""
            return [cell.upper() for cell in row]

        view = ListView(data, columns, output_mode=OutputMode.DATA)
        view.add_decorator(uppercase_decorator)

        output = view.render_data()
        assert "1" in output  # ID preserved
        assert "TEST" in output  # Value uppercased

    def test_multiple_decorators(self):
        """Test applying multiple decorators in order."""
        data = [{"id": "1", "value": "test"}]
        columns = [
            ColumnConfig(name="ID", field="id"),
            ColumnConfig(name="Value", field="value"),
        ]

        def add_prefix(row, obj):
            return [f"PRE_{cell}" for cell in row]

        def add_suffix(row, obj):
            return [f"{cell}_SUF" for cell in row]

        view = ListView(data, columns, output_mode=OutputMode.DATA)
        view.add_decorator(add_prefix)
        view.add_decorator(add_suffix)

        output = view.render_data()
        assert "PRE_1_SUF" in output
        assert "PRE_test_SUF" in output


class TestListViewStatusStyling:
    """Test status-based styling."""

    def test_get_status_from_dict(self):
        """Test extracting status from dict."""
        data = [{"id": "1", "status": "done"}]
        columns = [ColumnConfig(name="ID", field="id")]
        view = ListView(data, columns, status_field="status")

        status = view._get_status(data[0])
        assert status == "done"

    def test_get_status_from_object(self):
        """Test extracting status from object."""
        class Task:
            def __init__(self):
                self.status = "active"

        data = [Task()]
        columns = [ColumnConfig(name="Status", field="status")]
        view = ListView(data, columns, status_field="status")

        status = view._get_status(data[0])
        assert status == "active"

    def test_get_status_with_enum(self):
        """Test extracting status from enum value."""
        from enum import Enum

        class Status(Enum):
            ACTIVE = "active"
            DONE = "done"

        class Task:
            def __init__(self):
                self.status = Status.ACTIVE

        data = [Task()]
        columns = [ColumnConfig(name="Status", field="status")]
        view = ListView(data, columns, status_field="status")

        status = view._get_status(data[0])
        assert status == "active"
