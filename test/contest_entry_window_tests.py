"""The entry window's TAB cycle.

``TabOrder`` defaults to the fields the contest *shows*, so ``EntryFields`` is
the one list to keep in step; only a contest that shows a field but keeps it out
of the cycle names the order itself.  The corpus never covers tab order, so the
derived default and AGCW's override are pinned here.
"""

from __future__ import annotations

from not1mm.lib.contest import load_contest

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
        for name in ENTRY_FIELDS + WIDGETS + (
            "snt_label",
            "other_label",
            "exch_label",
        ):
            setattr(self, name, Widget(name))
        self.tab_next = {}
        self.tab_prev = {}


def started(plugin: str) -> Parent:
    """Load *plugin* and run the app's entry-window setup; return its parent."""
    parent = Parent()
    load_contest(plugin, parent).init_contest()
    return parent


def test_visible_fields_follow_entry_fields():
    """The shown fields are EntryFields, callsign first, in window order."""
    parent = Parent()
    contest = load_contest("ari_40_80", parent)
    assert contest.visible_fields() == ("callsign", "sent", "receive", "other_2")
    assert load_contest("ari_dx", Parent()).visible_fields() == ENTRY_FIELDS


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


def test_a_hidden_field_is_not_in_the_tab_cycle():
    """10-10 hides other_1, so the derived order skips it."""
    parent = started("10_10_fall_cw")
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.sent
    assert tab[parent.sent] is parent.receive
    assert tab[parent.receive] is parent.other_2  # not the hidden other_1
    assert tab[parent.other_2] is parent.callsign
    # the hidden field still has a destination, should focus land on it
    assert tab[parent.other_1] is parent.other_2


def test_shift_tab_reverses_the_derived_order():
    """Shift-TAB is the same cycle backwards."""
    parent = started("ari_40_80")
    prev = parent.tab_prev
    assert prev[parent.callsign] is parent.other_2
    assert prev[parent.other_2] is parent.receive
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
    assert parent.field1.shown and parent.field2.shown
    tab = parent.tab_next
    assert tab[parent.callsign] is parent.sent
    assert tab[parent.sent] is parent.receive
    assert tab[parent.receive] is parent.other_1
    assert tab[parent.other_1] is parent.other_2
    assert tab[parent.other_2] is parent.callsign
    prev = parent.tab_prev
    assert prev[parent.sent] is parent.callsign
    assert prev[parent.receive] is parent.sent
