"""
Unit tests for modern epics command.

Verifies ListView output works in DATA/AGENT modes using real TaskStorage.
"""

import json
from argparse import Namespace

from taskpy.legacy.storage import TaskStorage
from taskpy.modern.epics.commands import cmd_epics
from taskpy.modern.shared.output import set_output_mode, OutputMode


def _init_storage(tmp_path):
    """Initialize kanban storage in temp directory."""
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_cmd_epics_data_mode(tmp_path, monkeypatch, capsys):
    """List of epics should emit TSV output when DATA mode is enabled."""
    _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    set_output_mode(OutputMode.DATA)

    cmd_epics(Namespace())

    output = capsys.readouterr().out
    assert "Epic\tDescription" in output
    assert "FEAT" in output  # default epics from template
    assert "BUGS" in output


def test_cmd_epics_agent_mode(tmp_path, monkeypatch, capsys):
    """Agent mode should produce JSON with epic metadata."""
    _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    set_output_mode(OutputMode.AGENT)

    cmd_epics(Namespace())

    payload = json.loads(capsys.readouterr().out)
    assert payload["title"].startswith("Available Epics")
    assert payload["count"] >= 1
    assert any(item["Epic"] == "FEAT" for item in payload["items"])
