"""Unit tests for tags command."""

from argparse import Namespace

from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.tags.commands import cmd_tags


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def _create_task(storage: TaskStorage, task_id: str):
    task = Task(
        id=task_id,
        epic=task_id.split("-")[0],
        number=int(task_id.split("-")[1]),
        title="Task",
        status=TaskStatus.BACKLOG,
        priority=Priority.MEDIUM,
        story_points=1,
    )
    storage.write_task_file(task)


def test_tags_add_remove_set_clear(tmp_path, monkeypatch):
    storage = _init_storage(tmp_path)
    _create_task(storage, "TEST-01")
    _create_task(storage, "TEST-02")

    monkeypatch.chdir(tmp_path)

    # Add tags
    cmd_tags(Namespace(task_ids=["TEST-01,TEST-02"], list=False, add="ui,backend", remove=None, set_tags=None, clear=False))
    for tid in ["TEST-01", "TEST-02"]:
        task_path, _ = storage.find_task_file(tid)
        task = storage.read_task_file(task_path)
        assert set(task.tags) == {"ui", "backend"}

    # Remove one tag
    cmd_tags(Namespace(task_ids=["TEST-01"], list=False, add=None, remove="backend", set_tags=None, clear=False))
    task_path, _ = storage.find_task_file("TEST-01")
    task = storage.read_task_file(task_path)
    assert task.tags == ["ui"]

    # Set tags (override)
    cmd_tags(Namespace(task_ids=["TEST-01"], list=False, add=None, remove=None, set_tags="infra", clear=False))
    task_path, _ = storage.find_task_file("TEST-01")
    task = storage.read_task_file(task_path)
    assert task.tags == ["infra"]

    # Clear tags
    cmd_tags(Namespace(task_ids=["TEST-01"], list=False, add=None, remove=None, set_tags=None, clear=True))
    task_path, _ = storage.find_task_file("TEST-01")
    task = storage.read_task_file(task_path)
    assert task.tags == []
