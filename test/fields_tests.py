"""The entry-window boxes: the declaration, and the widgets built from it."""

from __future__ import annotations

import os

import pytest

# The widget tests below are the only ones that need a QApplication; keep them
# headless wherever the suite runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets
from PyQt6.QtGui import QFont

from not1mm.lib.contest import PLUGIN_PATH, load_contest
from not1mm.lib.fields import (
    DEFAULT_ENTRY_WINDOW,
    FIELD_SPECS,
    Fields,
    parse_entry_window_info,
)


class Parent:
    """Only what load_contest() needs; entry_boxes() never touches it."""


def plugin_names():
    return sorted(
        path.stem
        for path in PLUGIN_PATH.glob("*.py")
        if path.stem not in {"__init__", "base"}
    )


# -- the parsed declaration -------------------------------------------------


def test_n1mm_style_name_width_pairs():
    boxes = parse_entry_window_info(DEFAULT_ENTRY_WINDOW)
    assert [(box.spec.name, box.width) for box in boxes] == [
        ("SNTText", 450),
        ("RCVText", 450),
        ("SntNrText", 625),
        ("RcvNrText", 625),
    ]


def test_unknown_box_is_rejected():
    with pytest.raises(ValueError, match="unknown box"):
        parse_entry_window_info(("SentText", 450))


def test_odd_list_is_rejected():
    with pytest.raises(ValueError, match="name/width pairs"):
        parse_entry_window_info(("SNTText", 450, "RCVText"))


def test_duplicate_box_is_rejected():
    with pytest.raises(ValueError, match="declared twice"):
        parse_entry_window_info(("SNTText", 450, "SNTText", 450))


def test_all_udc_boxes_have_their_defaults():
    assert set(FIELD_SPECS) == {
        "SNTText",
        "RCVText",
        "SntNrText",
        "RcvNrText",
        "Exchange1Text",
        "MiscText",
        "SectText",
        "GridSquareText",
        "NameText",
        "CommentText",
    }
    assert FIELD_SPECS["CommentText"].space_advances is False
    assert FIELD_SPECS["CommentText"].max_length == 60


# -- the legacy description, against the pre-refactor snapshot --------------


def test_every_plugin_now_declares_its_entry_window():
    """The migration is complete: no plugin is left on the old description."""
    for plugin in plugin_names():
        assert load_contest(plugin, Parent()).EntryWindowInfo is not None, plugin


@pytest.fixture(scope="module")
def app():
    instance = QtWidgets.QApplication.instance()
    return instance or QtWidgets.QApplication([])


@pytest.fixture
def window(app):
    container = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(container)
    callsign_frame = QtWidgets.QFrame(container)
    callsign_frame.setObjectName("CallSignTextFrame")
    QtWidgets.QLabel("Callsign", callsign_frame).setObjectName("CallSignTextLabel")
    callsign = QtWidgets.QLineEdit(callsign_frame)
    callsign.setObjectName("CallSignText")
    callsign.setFont(QFont("JetBrains Mono", 20))
    layout.addWidget(callsign_frame, 900)
    yield layout, callsign_frame
    container.deleteLater()


def test_callsign_replaces_the_designer_placeholder(app, window):
    """The callsign is built with the row, after everything main.ui made."""
    layout, placeholder = window
    placeholder_edit = placeholder.findChild(QtWidgets.QLineEdit, "CallSignText")
    fields = Fields(layout, placeholder)
    assert fields.callsign_frame is not placeholder
    assert fields.callsign_frame.objectName() == "CallSignTextFrame"
    assert fields.callsign is not placeholder_edit
    assert layout.itemAt(0).widget() is fields.callsign_frame


def test_entry_font_follows_the_designer_box(app, window):
    """main.ui's font is carried to every box, including the rebuilt callsign."""
    layout, placeholder = window
    fields = Fields(layout, placeholder)
    for edit in (fields.callsign, fields.SNTText, fields.RcvNrText):
        assert edit.font().family() == "JetBrains Mono"
        assert edit.font().pointSize() == 20


def test_fields_build_the_declared_boxes_in_order(app, window):
    layout, callsign_frame = window
    fields = Fields(layout, callsign_frame)
    boxes = parse_entry_window_info(
        ("Exchange1Text", 800, "SectText", 400, "GridSquareText", 600)
    )
    assert fields.configure(boxes) is True

    assert fields.callsign.objectName() == "CallSignText"
    assert fields.CallSignText is fields.callsign
    assert fields.edit("CallSignText") is fields.callsign
    assert [field.name for field in fields] == [
        "Exchange1Text",
        "SectText",
        "GridSquareText",
    ]
    assert fields.display_order()[0] is fields.callsign
    # The named handle the rest of the application uses.
    assert fields.Exchange1Text is fields.edit("Exchange1Text")
    with pytest.raises(AttributeError):
        fields.MiscText
    # The containing layout: callsign first, then the declared boxes.
    assert [
        layout.itemAt(index).widget().objectName() for index in range(layout.count())
    ] == [
        "CallSignTextFrame",
        "Exchange1TextFrame",
        "SectTextFrame",
        "GridSquareTextFrame",
    ]


def test_fields_apply_labels_widths_and_lengths(app, window):
    layout, callsign_frame = window
    fields = Fields(layout, callsign_frame)
    boxes = parse_entry_window_info(("CommentText", 1695, "NameText", 855))
    boxes[0].label = "Remarks"
    boxes[0].accessible = "Remarks"
    fields.configure(boxes)

    # N1MM's maxima are metadata; the old window never truncated, and a grid
    # or a free-form exchange can be longer than the box's N1MM name suggests.
    assert fields.CommentText.maxLength() > 60
    assert fields.NameText.maxLength() > 20
    assert fields.field("CommentText").label.text() == "Remarks"
    assert fields.CommentText.accessibleName() == "Remarks"
    assert layout.stretch(1) == 1695
    assert layout.stretch(2) == 855


def test_rebuild_keeps_the_callsign_and_the_same_row_keeps_its_text(app, window):
    layout, callsign_frame = window
    fields = Fields(layout, callsign_frame)
    fields.configure(parse_entry_window_info(DEFAULT_ENTRY_WINDOW))
    fields.SntNrText.setText("42")
    callsign = fields.callsign

    # A different contest with the same boxes only relabels: not a rebuild.
    boxes = parse_entry_window_info(DEFAULT_ENTRY_WINDOW)
    boxes[2].label = "Serial"
    assert fields.configure(boxes) is False
    assert fields.SntNrText.text() == "42"
    assert fields.callsign is callsign

    # A different row rebuilds, and the callsign widget survives.
    assert fields.configure(parse_entry_window_info(("NameText", 855))) is True
    assert fields.callsign is callsign
    assert fields.names() == ("NameText",)
    assert fields.edit("SntNrText") is None
