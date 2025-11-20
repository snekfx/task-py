"""Unit tests for modern linking commands."""

from argparse import Namespace

from taskpy.legacy.models import Task, TaskStatus, Priority
from taskpy.legacy.storage import TaskStorage
from taskpy.modern.linking.commands import cmd_link
from taskpy.modern.shared.output import set_output_mode, OutputMode


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_link_multiple_tasks(tmp_path, monkeypatch):
    """cmd_link should accept comma/space separated IDs."""
    storage = _init_storage(tmp_path)

    for i in range(2):
        task = Task(
            id=f"TEST-0{i+1}",
            epic="TEST",
            number=i + 1,
            title="Link test",
            status=TaskStatus.BACKLOG,
            priority=Priority.MEDIUM,
            story_points=1,
        )
        storage.write_task_file(task)

    args = Namespace(
        task_ids=["TEST-01,TEST-02"],
        code=["src/code.py"],
        docs=None,
        plan=None,
        test=["tests/test_code.py"],
        nfr=None,
        verify=["pytest -q"],
        commit=None,
        issue=None,
    )

    monkeypatch.chdir(tmp_path)
    set_output_mode(OutputMode.DATA)
    cmd_link(args)

    for tid in ["TEST-01", "TEST-02"]:
        path, _ = storage.find_task_file(tid)
        task = storage.read_task_file(path)
        assert "src/code.py" in task.references.code
        assert "tests/test_code.py" in task.references.tests
        assert task.verification.command == "pytest -q"
