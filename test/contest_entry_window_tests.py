"""The entry window's TAB/SPACE cycle.

The cycle comes from the boxes the contest shows: ``EntryFields`` while a
plugin still uses the old four-frame description, ``EntryWindowInfo`` once it
has moved to named boxes.  The corpus never covers tab order, so the derived
default and AGCW's all-four case are pinned here.
"""

from __future__ import annotations

from contest_harness import FakeFields
from not1mm.lib.contest import ContestBase, load_contest

ENTRY_FIELDS = ("callsign", "sent", "receive", "other_1", "other_2")
WIDGETS = ("field1", "field2", "field3", "field4")


class Widget:
    """A stand-in entry field, remembering whether it was shown or hidden."""

    def __init__(self, name):
        self.name = name
        self.shown = True

    def show(self):
        self.shown = True

    def hide(self):
        self.shown = False

    def setText(self, *args):  # noqa: N802
        ...

    def setAccessibleName(self, *args):  # noqa: N802
        ...

    def __bool__(self):
        return True


class Parent:
    """Just enough of the main window for init_contest()."""

    def __init__(self):
        for name in ENTRY_FIELDS:
            setattr(self, name, Widget(name))
        self.fields = FakeFields(self)
        self.after_fields_rebuilt = lambda: None
        self.set_running = lambda _running: None
        self.station = {}
        self.tab_next = {}
        self.tab_prev = {}


def started(plugin: str) -> Parent:
    """Load *plugin* and run the app's entry-window setup; return its parent."""
    parent = Parent()
    load_contest(plugin, parent).init_contest()
    return parent


def test_visible_fields_follow_entry_fields():
    """The shown boxes are the ones the old four frames describe."""
    parent = Parent()
    contest = load_contest("ari_40_80", parent)
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


def test_advance_on_space_defaults_to_separating():
    """A space separates by default; a contest whose exchange has spaces says so."""
    assert load_contest("ari_dx", Parent()).advance_on_space == [True] * 5
    assert load_contest("10_10_fall_cw", Parent()).advance_on_space == [
        True,
        True,
        True,
        False,
        False,
    ]


class HiddenFieldsContest(ContestBase):
    """A legacy description that hides the second report and the last box."""

    EntryFields = ("field1", "field3")


def test_a_hidden_field_is_not_in_the_tab_cycle():
    """A hidden box is skipped; it still has a destination."""
    parent = Parent()
    HiddenFieldsContest(parent).init_contest()
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.sent
    assert tab[parent.sent] is parent.other_1
    assert tab[parent.other_1] is parent.callsign
    # the hidden fields still have a destination, should focus land on them
    assert tab[parent.receive] is parent.other_1
    assert tab[parent.other_2] is parent.callsign


def test_a_lookup_lands_on_the_first_field_to_fill():
    """NextField defaults to the first box that is not a report or SentNR."""
    parent = started("naqp_cw")
    assert parent.next_field is parent.fields.edit("NameText")
    parent = started("10_10_fall_cw")
    assert parent.next_field is parent.fields.edit("Exchange1Text")
    parent = started("ari_dx")
    assert parent.next_field is parent.fields.edit("RcvNrText")


def test_shift_tab_reverses_the_derived_order():
    """Shift-TAB is the same cycle backwards."""
    parent = started("ari_40_80")
    exchange = parent.fields.edit("Exchange1Text")
    prev = parent.tab_prev
    assert prev[parent.callsign] is exchange
    assert prev[exchange] is parent.receive
    assert prev[parent.receive] is parent.sent
    assert prev[parent.sent] is parent.callsign


def test_the_default_order_is_the_window_order():
    """A contest that shows every field walks them in the window's order."""
    parent = started("ari_dx")
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.sent
    assert tab[parent.sent] is parent.receive
    assert tab[parent.receive] is parent.other_1
    assert tab[parent.other_1] is parent.other_2
    assert tab[parent.other_2] is parent.callsign


def test_agcw_tabs_through_every_visible_field():
    """AGCW shows the RST fields, and TAB walks them like every other contest."""
    parent = started("agcw_qrp")
    assert "SNTText" in parent.fields.names()
    assert "RCVText" in parent.fields.names()
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.sent
    assert tab[parent.sent] is parent.receive
    assert tab[parent.receive] is parent.other_1
    assert tab[parent.other_1] is parent.other_2
    assert tab[parent.other_2] is parent.callsign
    prev = parent.tab_prev
    assert prev[parent.sent] is parent.callsign
    assert prev[parent.receive] is parent.sent
