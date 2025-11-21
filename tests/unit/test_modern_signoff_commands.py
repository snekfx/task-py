"""Tests for signoff list management commands."""

from argparse import Namespace
import re

from taskpy.legacy.storage import TaskStorage
from taskpy.modern.signoff.commands import cmd_signoff
from taskpy.modern.shared.config import load_signoff_list


def _init(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_signoff_add_and_list(tmp_path, monkeypatch, capsys):
    storage = _init(tmp_path)
    monkeypatch.chdir(tmp_path)

    # Initially empty
    cmd_signoff(Namespace(signoff_action="list", task_ids=None))
    out = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "No tickets" in out

    # Add tickets
    cmd_signoff(Namespace(signoff_action="add", task_ids=["FEAT-01,BUGS-02"]))
    tickets = load_signoff_list(tmp_path)
    assert tickets == ["BUGS-02", "FEAT-01"] or tickets == ["FEAT-01", "BUGS-02"]

    # List shows both
    capsys.readouterr()
    cmd_signoff(Namespace(signoff_action="list", task_ids=None))
    out = capsys.readouterr().out
    assert "FEAT-01" in out
    assert "BUGS-02" in out

    # Remove one
    cmd_signoff(Namespace(signoff_action="remove", task_ids=["BUGS-02"]))
    tickets = load_signoff_list(tmp_path)
    assert tickets == ["FEAT-01"]
