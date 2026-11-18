"""The entry-window boxes: the declaration, and the widgets built from it.

``test/data/entry_window_snapshot.json`` was captured from the old fixed
window before the fields refactor: for every plugin, which of the four frames
it showed, the label each showed, and the screen-reader names.  A plugin that
has not migrated yet must still describe exactly that, so the snapshot is the
invariant the migration keeps.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# The widget tests below are the only ones that need a QApplication; keep them
# headless wherever the suite runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6 import QtWidgets

from not1mm.lib.contest import load_contest
from not1mm.lib.fields import (
    DEFAULT_ENTRY_WINDOW,
    FIELD_SPECS,
    Fields,
    legacy_entry_boxes,
    parse_entry_window_info,
)

SNAPSHOT = json.loads(
    (Path(__file__).parent / "data" / "entry_window_snapshot.json").read_text(
        encoding="utf-8"
    )
)
LEGACY_NAMES = ("SNTText", "RCVText", "SntNrText", "RcvNrText")
LEGACY_WIDGETS = ("field1", "field2", "field3", "field4")
LABEL_KEYS = ("snt_label", "rcv_label", "other_label", "exch_label")
ACCESSIBLE_KEYS = ("sent", "receive", "other_1", "other_2")


class Parent:
    """Only what load_contest() needs; entry_boxes() never touches it."""


def plugin_names():
    return sorted(SNAPSHOT["plugins"])


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


def test_every_unmigrated_plugin_still_describes_its_old_window():
    """No visible change for a plugin still on the old four-frame description.

    A batch that migrates a plugin to EntryWindowInfo takes it out of this
    comparison, so the fixture shrinks with the migration instead of having to
    be edited.
    """
    checked = 0
    for plugin in plugin_names():
        contest = load_contest(plugin, Parent())
        if contest.EntryWindowInfo is not None:
            continue
        expected = SNAPSHOT["plugins"][plugin]
        boxes = contest.entry_boxes()
        checked += 1
        assert [box.spec.name for box in boxes] == list(LEGACY_NAMES), plugin
        assert [name for name, box in zip(LEGACY_NAMES, boxes) if box.visible] == [
            LEGACY_NAMES[LEGACY_WIDGETS.index(widget)] for widget in expected["visible"]
        ], plugin
        assert [box.label for box in boxes] == [
            expected["labels"][key] for key in LABEL_KEYS
        ], plugin
        assert [box.accessible for box in boxes] == [
            expected["accessible"][key] for key in ACCESSIBLE_KEYS
        ], plugin
    # The list shrinks with each migration batch; it must not be empty until
    # Phase 3 deletes the legacy description entirely.
    assert checked


def test_legacy_boxes_keep_the_old_defaults():
    boxes = legacy_entry_boxes(LEGACY_WIDGETS)
    assert [box.label for box in boxes] == ["SNT", "RCV", "SentNR", "RcvNR"]
    assert [box.accessible for box in boxes] == [
        "RST Sent",
        "",
        "Sent Number",
        "Received Number",
    ]
    assert [box.spec.max_length for box in boxes] == [10, 15, 5, 5]


def test_legacy_frame_text_and_rcv_label():
    boxes = legacy_entry_boxes(
        ("field3", "field4"),
        ("", "Name", "State"),
        "RcvNR",
        ("", "", "Name", "State"),
    )
    assert [box.visible for box in boxes] == [False, False, True, True]
    assert [box.label for box in boxes] == ["SNT", "RcvNR", "Name", "State"]
    assert [box.accessible for box in boxes] == ["", "", "Name", "State"]


# -- the widgets ------------------------------------------------------------


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

    assert fields.CommentText.maxLength() == 60
    assert fields.NameText.maxLength() == 20
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


def test_legacy_aliases_and_report_edits(app, window):
    layout, callsign_frame = window
    fields = Fields(layout, callsign_frame)
    fields.configure(
        legacy_entry_boxes(("field1", "field2", "field3", "field4")), legacy=True
    )
    assert fields.legacy_edit("other_1") is fields.SntNrText
    assert fields.legacy_edit("other_2") is fields.RcvNrText
    assert fields.report_edits() == (fields.SNTText, fields.RCVText)
    assert fields.inputs()[fields.callsign] == "callsign"

    # A migrated contest has no fixed slots: the first two non-report boxes
    # stand in for other_1/other_2.
    fields.configure(
        parse_entry_window_info(("NameText", 855, "SectText", 600)), legacy=False
    )
    assert fields.legacy_edit("other_1") is fields.NameText
    assert fields.legacy_edit("other_2") is fields.SectText
    assert fields.report_edits() == ()
