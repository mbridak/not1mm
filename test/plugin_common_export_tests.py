"""Tests for the log export save dialog helper."""

import types
from pathlib import Path
from unittest.mock import patch

from not1mm.lib import plugin_common


def run_helper(pref, result):
    """Run the helper with a fake dialog. Return the path and the dialog start path."""
    app = types.SimpleNamespace(pref=pref)
    with (
        patch.object(
            plugin_common.QFileDialog, "getSaveFileName", return_value=(result, "")
        ) as dialog,
        patch.object(plugin_common.Preferences, "save") as save,
    ):
        filename = plugin_common.get_export_filename(app, "K1ABC.log", "*.log")
    return filename, dialog.call_args.args[2], save.called


def test_no_stored_dir_uses_home():
    _, start, _ = run_helper({}, "")
    assert start == str(Path.home() / "K1ABC.log")


def test_missing_dir_uses_home(tmp_path):
    _, start, _ = run_helper({"export_dir": str(tmp_path / "gone")}, "")
    assert start == str(Path.home() / "K1ABC.log")


def test_stored_dir_is_used_and_updated(tmp_path):
    new_dir = tmp_path / "new"
    pref = {"export_dir": str(tmp_path)}
    filename, start, saved = run_helper(pref, str(new_dir / "K1ABC.log"))
    assert start == str(tmp_path / "K1ABC.log")
    assert filename == str(new_dir / "K1ABC.log")
    assert pref["export_dir"] == str(new_dir)
    assert saved


def test_cancel_returns_none(tmp_path):
    pref = {"export_dir": str(tmp_path)}
    filename, _, saved = run_helper(pref, "")
    assert filename is None
    assert pref["export_dir"] == str(tmp_path)
    assert not saved
