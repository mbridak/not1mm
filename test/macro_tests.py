"""The contest macro directory, and the no-contest case.

``poll_radio()`` can call ``setmode()`` → ``read_macros()`` before a contest
has been loaded, so asking for the macro file must not touch ``BaseName``.
"""

from __future__ import annotations

from types import SimpleNamespace

from not1mm.__main__ import MainWindow


def test_a_radio_poll_before_a_contest_has_no_macro_file():
    parent = SimpleNamespace(radio_state={"mode": "CW"}, contest=None)
    assert MainWindow.get_macro_filename(parent) == ""
