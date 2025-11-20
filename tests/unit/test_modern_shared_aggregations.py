"""Tests for shared aggregation helpers."""

from taskpy.modern.shared import aggregations as agg


ROWS = [
    {
        "id": "FEAT-01",
        "status": "backlog",
        "priority": "high",
        "story_points": "3",
        "epic": "FEAT",
        "in_sprint": "true",
        "milestone": "milestone-1",
    },
    {
        "id": "BUGS-01",
        "status": "active",
        "priority": "critical",
        "story_points": "2",
        "epic": "BUGS",
        "in_sprint": "true",
        "milestone": "",
    },
    {
        "id": "DOCS-01",
        "status": "done",
        "priority": "low",
        "story_points": "1",
        "epic": "DOCS",
        "in_sprint": "false",
        "milestone": "milestone-1",
    },
]


def test_count_helpers():
    assert agg.count_by_status(ROWS)["backlog"] == 1
    assert agg.count_by_priority(ROWS)["critical"] == 1
    assert agg.count_by_epic(ROWS)["BUGS"] == 1


def test_sum_helpers():
    assert agg.sum_story_points(ROWS) == 6
    by_status = agg.sum_story_points_by_status(ROWS)
    assert by_status["done"] == 1
    assert by_status["active"] == 2


def test_filter_helpers():
    backlog = agg.filter_by_status(ROWS, "backlog")
    assert backlog[0]["id"] == "FEAT-01"

    only_bug = agg.filter_by_epic(ROWS, "BUGS")
    assert only_bug[0]["id"] == "BUGS-01"

    sprint_rows = agg.filter_by_sprint(ROWS, True)
    assert len(sprint_rows) == 2

    milestone_rows = agg.filter_by_milestone(ROWS, "milestone-1")
    assert len(milestone_rows) == 2


def test_project_stats():
    stats = agg.get_project_stats(ROWS)
    assert stats["total_tasks"] == 3
    assert stats["total_story_points"] == 6
    assert stats["by_status"]["done"] == 1


def test_sprint_stats():
    stats = agg.get_sprint_stats(agg.filter_by_sprint(ROWS, True))
    assert stats["total_tasks"] == 2
    assert stats["by_priority"]["critical"] == 1


def test_milestone_stats():
    rows = agg.filter_by_milestone(ROWS, "milestone-1")
    stats = agg.get_milestone_stats(rows)
    assert stats["total_tasks"] == 2
    assert stats["completed_tasks"] == 1
    assert stats["story_points_completed"] == 1
