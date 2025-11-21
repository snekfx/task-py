"""Unit tests for feature flag commands."""

import re
from argparse import Namespace

from taskpy.legacy.storage import TaskStorage
from taskpy.modern.flags.commands import cmd_flag
from taskpy.modern.shared.config import load_feature_flags


def _init_storage(tmp_path):
    storage = TaskStorage(tmp_path)
    storage.initialize()
    return storage


def test_flag_enable_and_disable(tmp_path, monkeypatch):
    """Enable/disable should persist strict_mode flag."""
    _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    cmd_flag(Namespace(flag_action="enable", flag_name="strict_mode"))
    flags = load_feature_flags(tmp_path)
    assert flags.get("strict_mode") is True

    cmd_flag(Namespace(flag_action="disable", flag_name="strict_mode"))
    flags = load_feature_flags(tmp_path)
    assert flags.get("strict_mode") is False


def test_flag_list_reports_status(tmp_path, monkeypatch, capsys):
    """List action should show configured feature flags."""
    _init_storage(tmp_path)
    monkeypatch.chdir(tmp_path)

    cmd_flag(Namespace(flag_action="enable", flag_name="strict_mode"))
    capsys.readouterr()  # clear enable output
    cmd_flag(Namespace(flag_action="list", flag_name=None))

    output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "strict_mode" in output
    assert "on" in output or "enabled" in output.lower()
