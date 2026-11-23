"""The entry window's TAB/SPACE cycle.

The cycle comes from the boxes the contest declares in ``EntryWindowInfo``, in
that order, with the callsign first.  The corpus never covers tab order, so the
derived order is pinned here.
"""

from __future__ import annotations

from contest_harness import FakeFields
from not1mm.lib.contest import load_contest


class Widget:
    """The callsign widget; the exchange boxes come from FakeFields."""

    def __init__(self, name):
        self.name = name

    def setText(self, *args):  # noqa: N802
        ...

    def setAccessibleName(self, *args):  # noqa: N802
        ...

    def __bool__(self):
        return True


class Parent:
    """Just enough of the main window for init_contest()."""

    def __init__(self):
        self.callsign = Widget("callsign")
        self.fields = FakeFields(self)
        self.after_fields_rebuilt = lambda: None
        self.set_running = lambda _running: None
        self.station = {}
        self.tab_next = {}


def started(plugin: str) -> Parent:
    """Load *plugin* and run the app's entry-window setup; return its parent."""
    parent = Parent()
    load_contest(plugin, parent).init_contest()
    return parent


def test_visible_fields_follow_the_declaration():
    contest = load_contest("ari_40_80", Parent())
    assert contest.visible_fields() == (
        "callsign",
        "SNTText",
        "RCVText",
        "Exchange1Text",
    )
    assert load_contest("ari_dx", Parent()).visible_fields() == (
        "callsign",
        "SNTText",
        "RCVText",
        "SntNrText",
        "RcvNrText",
    )


def test_space_keeps_focus_only_where_declared():
    assert load_contest("ari_dx", Parent()).SpaceKeepsFocus == ()
    assert load_contest("10_10_fall_cw", Parent()).SpaceKeepsFocus == ("Exchange1Text",)


def test_tab_walks_the_declared_boxes():
    parent = started("ari_dx")
    sent = parent.fields.edit("SNTText")
    receive = parent.fields.edit("RCVText")
    sent_nr = parent.fields.edit("SntNrText")
    rcv_nr = parent.fields.edit("RcvNrText")
    tab = parent.tab_next
    assert tab[parent.callsign] is sent
    assert tab[sent] is receive
    assert tab[receive] is sent_nr
    assert tab[sent_nr] is rcv_nr
    assert tab[rcv_nr] is parent.callsign

    parent = started("10_10_fall_cw")
    sent = parent.fields.edit("SNTText")
    receive = parent.fields.edit("RCVText")
    exchange = parent.fields.edit("Exchange1Text")
    tab = parent.tab_next
    assert tab[parent.callsign] is sent
    assert tab[sent] is receive
    assert tab[receive] is exchange
    assert tab[exchange] is parent.callsign


def test_a_lookup_lands_on_the_first_field_to_fill():
    """NextField defaults to the first box that is not a report or SentNR."""
    parent = started("naqp_cw")
    assert parent.next_field is parent.fields.edit("NameText")
    parent = started("10_10_fall_cw")
    assert parent.next_field is parent.fields.edit("Exchange1Text")
    parent = started("ari_dx")
    assert parent.next_field is parent.fields.edit("RcvNrText")


def test_agcw_tabs_through_every_box():
    parent = started("agcw_qrp")
    names = parent.fields.names()
    assert names == ("SNTText", "RCVText", "SntNrText", "RcvNrText")
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.fields.edit("SNTText")
    assert tab[parent.fields.edit("RcvNrText")] is parent.callsign
