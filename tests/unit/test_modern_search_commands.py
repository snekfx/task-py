"""Tests for search command."""

import json
from argparse import Namespace

from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.search.commands import cmd_search
from taskpy.modern.shared.output import set_output_mode, OutputMode


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def _task(storage, task_id, title, status=TaskStatus.BACKLOG, tags=None, content="body"):
    task = Task(
        id=task_id,
        epic=task_id.split("-")[0],
        number=int(task_id.split("-")[1]),
        title=title,
        status=status,
        priority=Priority.MEDIUM,
        story_points=1,
        content=content,
        tags=tags or [],
    )
    storage.write_task_file(task)


def test_search_matches_title_and_tags(tmp_path, monkeypatch, capsys):
    storage = _init_storage(tmp_path)
    _task(storage, "FEAT-01", "Implement API", tags=["backend"])
    _task(storage, "FEAT-02", "Improve UI", tags=["frontend"])

    monkeypatch.chdir(tmp_path)
    set_output_mode(OutputMode.DATA)
    cmd_search(Namespace(
        keywords=["api"],
        filters=None,
        status=None,
        epic=None,
        in_sprint=False,
        archived=False,
    ))
    out = capsys.readouterr().out.lower()
    assert "implement api" in out
    assert "tags: backend" in out


def test_search_filter_tags_only(tmp_path, monkeypatch, capsys):
    storage = _init_storage(tmp_path)
    _task(storage, "FEAT-01", "Implement API", tags=["backend"])
    _task(storage, "FEAT-02", "Improve UI", tags=["frontend"])

    monkeypatch.chdir(tmp_path)
    set_output_mode(OutputMode.DATA)
    cmd_search(Namespace(
        keywords=["frontend"],
        filters="tags",
        status=None,
        epic=None,
        in_sprint=False,
        archived=False,
    ))
    out = capsys.readouterr().out
    assert "FEAT-02" in out
    assert "FEAT-01" not in out


def test_search_includes_archived_with_flag(tmp_path, monkeypatch, capsys):
    storage = _init_storage(tmp_path)
    _task(storage, "FEAT-01", "Implement API", status=TaskStatus.ARCHIVED, tags=["archived"])
    _task(storage, "FEAT-02", "Improve UI", status=TaskStatus.BACKLOG, tags=["frontend"])

    monkeypatch.chdir(tmp_path)
    set_output_mode(OutputMode.AGENT)
    cmd_search(Namespace(
        keywords=["implement"],
        filters=None,
        status=None,
        epic=None,
        in_sprint=False,
        archived=True,
    ))
    payload = json.loads(capsys.readouterr().out)
    ids = [item["id"] for item in payload["items"]]
    assert "FEAT-01" in ids
