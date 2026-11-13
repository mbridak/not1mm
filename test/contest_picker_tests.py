"""The New Contest picker, built from the plugins instead of the .ui file.

Discovery already knew every contest; these tests pin the extra step that turns
that registry into what an operator sees: the label rule, the order, the item
data the database reads back, and what a broken plugin must not do to the rest.
"""

from __future__ import annotations

import pytest

from not1mm.lib import contest
from not1mm.lib.new_contest import fill_picker


class StubCombo:
    """Just enough of a Qt combo box for ``fill_picker``."""

    def __init__(self, stale=()):
        self.items = list(stale)

    def clear(self):
        self.items.clear()

    def addItem(self, label, identifier=None):  # noqa: N802 -- Qt spelling
        self.items.append((label, identifier))


def test_the_picker_offers_every_contest():
    entries = contest.contest_picker_entries()
    available = contest.available_contests()
    assert len(entries) == len(available)
    assert {identifier for _, identifier in entries} == {
        info.identifier for info in available
    }


def test_labels_and_identifiers_are_unique():
    entries = contest.contest_picker_entries()
    labels = [label for label, _ in entries]
    identifiers = [identifier for _, identifier in entries]
    assert len(set(labels)) == len(labels)
    assert len(set(identifiers)) == len(identifiers)


@pytest.mark.parametrize(
    "display_name,cabrillo_name,expected",
    [
        # Same name bar case, spaces and dashes: no parenthetical.
        ("CQ WPX CW", "CQ-WPX-CW", "CQ WPX CW"),
        ("LZ DX", "LZ-DX", "LZ DX"),
        # Really different names: the Cabrillo name is worth showing.
        ("ARI International DX", "ARI-DX", "ARI International DX (ARI-DX)"),
        ("DARC SCHWABEN", "Schwaben Contest", "DARC SCHWABEN (Schwaben Contest)"),
        ("OK1WC Memorial Contest", "MWC", "OK1WC Memorial Contest (MWC)"),
    ],
)
def test_the_label_rule(display_name, cabrillo_name, expected):
    assert contest.contest_picker_label(display_name, cabrillo_name) == expected


def test_a_shared_cabrillo_name_stays_two_entries():
    """Pairs that share a Cabrillo name name themselves and stay distinct."""
    labels = dict(
        (identifier, label) for label, identifier in contest.contest_picker_entries()
    )
    assert labels["10_10_fall_cw"] == "10 10 FALL CW (10-10-SPRINT)"
    assert labels["10_10_spring_cw"] == "10 10 SPRING CW (10-10-SPRINT)"
    assert labels["qso_party_rst"] == "QSO PARTY RST (QSO_PARTY)"
    assert labels["qso_party_sn"] == "QSO PARTY SN (QSO_PARTY)"


def test_modes_come_before_the_contests():
    """General Logging and DX-Pedition are modes, and say so with SortOrder.

    Everything else keeps the default, so the ordering is a property of the
    two things that are not contests rather than of every plugin.
    """
    info = {i.source: i for i in contest.available_contests()}
    assert info["general_logging"].sort_order == 50
    assert info["dxpedition"].sort_order == 60
    assert all(
        i.sort_order == 100
        for source, i in info.items()
        if source not in ("general_logging", "dxpedition")
    )

    entries = contest.contest_picker_entries()
    assert entries[:2] == [
        ("General Logging", "General-Logging"),
        ("DX-Pedition", "DX-Pedition"),
    ]


def test_the_rest_is_ordered_by_sort_order_then_display_name():
    info = {i.identifier: i for i in contest.available_contests()}
    keys = [
        (info[identifier].sort_order, info[identifier].display_name.casefold())
        for _, identifier in contest.contest_picker_entries()
    ]
    assert keys == sorted(keys)


def test_a_plugin_that_does_not_load_is_left_out():
    """The picker opens on the rest of the contests, with a warning."""
    real = contest._contest_info

    def broken(source):
        if source == "ok1wc":
            raise RuntimeError("this plugin is broken")
        return real(source)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(contest, "_contest_info", broken)
        sources = {info.source for info in contest._scan_contests(tolerant=True)}
        assert "ok1wc" not in sources
        assert len(sources) == len(contest.available_contests()) - 1
        # The strict registry still refuses to pretend nothing happened.
        with pytest.raises(RuntimeError):
            contest._scan_contests()


def test_fill_picker_puts_the_identifier_in_the_item_data():
    combo = StubCombo(stale=[("old label", "old-identifier")])
    fill_picker(combo)
    assert combo.items == contest.contest_picker_entries()


def test_a_stored_identifier_can_be_shown_as_the_picker_label():
    assert contest.contest_label_for_identifier("MWC") == "OK1WC Memorial Contest (MWC)"
    # Old databases stored the name of the file the contest lives in.
    assert (
        contest.contest_label_for_identifier("ok1wc") == "OK1WC Memorial Contest (MWC)"
    )
    # Nothing installed answers to this, so it keeps its stored name.
    assert contest.contest_label_for_identifier("no-such-thing") == "no-such-thing"
    # The column is nullable; the list always wants something to show.
    assert contest.contest_label_for_identifier(None) == ""
    assert contest.contest_label_for_identifier(1) == "1"


def test_a_broken_plugin_does_not_break_the_saved_contest_list(monkeypatch):
    """Showing one saved name must not need every plugin to load."""

    def broken():
        raise RuntimeError("this plugin is broken")

    monkeypatch.setattr(contest, "available_contests", broken)
    assert contest.contest_label_for_identifier("MWC") == "OK1WC Memorial Contest (MWC)"
    assert contest.contest_label_for_identifier("no-such-thing") == "no-such-thing"
