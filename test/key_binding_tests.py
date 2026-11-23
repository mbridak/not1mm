"""Key-binding scopes: the aggregates, plus optional per-box contexts."""

from __future__ import annotations

from types import SimpleNamespace

from contest_harness import FakeFields
from not1mm.lib.fields import (
    DEFAULT_ENTRY_WINDOW,
    FIELD_SPECS,
    binding_contexts,
    parse_entry_window_info,
)


class Callsign:
    pass


def _fields(info=DEFAULT_ENTRY_WINDOW):
    parent = SimpleNamespace(callsign=Callsign())
    fields = FakeFields(parent)
    fields.configure(parse_entry_window_info(info))
    return fields


def test_the_standard_four_keep_the_aggregate_scopes():
    fields = _fields()
    cw = object()
    callsign = fields.callsign

    assert binding_contexts(fields, callsign, cw, callsign) == ("Callsign",)
    assert binding_contexts(fields, callsign, cw, fields.SNTText) == (
        "SNTText",
        "Report",
    )
    assert binding_contexts(fields, callsign, cw, fields.RCVText) == (
        "RCVText",
        "Report",
    )
    assert binding_contexts(fields, callsign, cw, fields.SntNrText) == (
        "SntNrText",
        "Other 1",
        "Exchange",
    )
    assert binding_contexts(fields, callsign, cw, fields.RcvNrText) == (
        "RcvNrText",
        "Other 2",
        "Exchange",
    )
    assert binding_contexts(fields, callsign, cw, cw) == ("CW entry",)


def test_a_two_box_contest_has_no_second_other_scope():
    fields = _fields(("NameText", 855, "SectText", 600))
    cw = object()
    callsign = fields.callsign
    assert binding_contexts(fields, callsign, cw, fields.NameText) == (
        "NameText",
        "Other 1",
        "Exchange",
    )
    assert binding_contexts(fields, callsign, cw, fields.SectText) == (
        "SectText",
        "Other 2",
        "Exchange",
    )


def test_a_three_box_contest_has_one_extra():
    fields = _fields(("SNTText", 450, "RCVText", 450, "Exchange1Text", 615))
    cw = object()
    callsign = fields.callsign
    assert binding_contexts(fields, callsign, cw, fields.Exchange1Text) == (
        "Exchange1Text",
        "Other 1",
        "Exchange",
    )


def test_the_edit_keys_dialog_offers_every_box():
    import not1mm.actions  # noqa: F401 - loads edit_keys past its cycle
    from not1mm.lib.edit_keys import _KNOWN_CONTEXTS

    for name in FIELD_SPECS:
        assert name in _KNOWN_CONTEXTS
    for aggregate in (
        "*",
        "Callsign",
        "Report",
        "Exchange",
        "Other 1",
        "Other 2",
        "CW entry",
    ):
        assert aggregate in _KNOWN_CONTEXTS
