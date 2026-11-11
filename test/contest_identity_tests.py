"""How a contest is named, and how it is found again.

A contest is identified by its Cabrillo name -- that is what the sponsor's log
checker recognises, so it is what the database, the log filenames and the
per-contest directory under ``~/.local/share/not1mm`` use.  A contest that
shares its Cabrillo name with another but is not interchangeable (the two
generic QSO party templates, the fall and spring Ten-Ten sprints) declares
``ContestName`` instead.

The identifiers the database has accumulated over the years are not all
Cabrillo names -- they used to be the name of the file the contest lived in --
so looking a contest up has to keep accepting those.
"""

from __future__ import annotations

import pytest

from not1mm.lib import contest

# The CQ WPX CW plugin is a class; everything else is still a module.
CONVERTED = "cq_wpx_cw"
LEGACY = "spdx"


def test_id_is_the_cabrillo_name():
    assert contest.contest_id(contest.contest_metadata(CONVERTED)) == "CQ-WPX-CW"
    assert contest.contest_id(contest.contest_metadata(LEGACY)) == "SPDX"


def test_a_contest_can_override_its_id():
    # The two templates share the Cabrillo name QSO_PARTY but are not
    # interchangeable, so they name themselves.
    rst = contest.contest_metadata("qso_party_rst")
    sn = contest.contest_metadata("qso_party_sn")
    assert rst.cabrillo_name == sn.cabrillo_name == "QSO_PARTY"
    assert contest.contest_id(rst) == "qso_party_rst"
    assert contest.contest_id(sn) == "qso_party_sn"


@pytest.mark.parametrize(
    "identifier,expected",
    [
        ("CQ-WPX-CW", "CQ-WPX-CW"),
        ("FD CW", "FD_CW"),
        ("Schwaben Contest", "Schwaben_Contest"),
        ("10-10-SPRINT", "10-10-SPRINT"),
    ],
)
def test_a_path_name_has_no_spaces(identifier, expected):
    assert contest.path_name(identifier) == expected


@pytest.mark.parametrize(
    "asked_for",
    [
        "cq_wpx_cw",  # the file it lives in, which is what the database used to store
        "CQ-WPX-CW",  # the identifier
        "cq-wpx-cw",  # ... matched without case
        "CQ WPX CW",  # the display name
    ],
)
def test_a_contest_is_found_by_any_of_its_names(asked_for):
    loaded = contest.load_contest(asked_for, None)
    assert contest.contest_id(loaded) == "CQ-WPX-CW"
    assert loaded.name == "CQ WPX CW"


def test_an_unknown_contest_is_an_error():
    with pytest.raises(ModuleNotFoundError):
        contest.load_contest("no such contest", None)


def test_a_missing_identifier_is_an_error():
    for nothing in (None, ""):
        with pytest.raises(ModuleNotFoundError):
            contest.load_contest(nothing, None)


def test_an_old_stored_value_still_resolves():
    # What the database holds today is the folded label, e.g. "ok1wc"; it has
    # to keep loading, and mean the same contest as the new identifier.
    assert contest.contest_id(contest.load_contest("ok1wc", None)) == "MWC"
    assert contest.contest_id(contest.load_contest("cq_wpx_cw", None)) == "CQ-WPX-CW"


def test_every_contest_declares_an_identifier():
    available = contest.available_contests()
    assert len(available) == 96
    assert len({info.source for info in available}) == len(available)
    for info in available:
        assert info.identifier, info.source
        assert info.display_name, info.source


def test_every_contest_can_be_loaded_by_its_identifier():
    for info in contest.available_contests():
        loaded = contest.load_contest(info.identifier, None)
        assert contest.contest_id(loaded) == info.identifier


def test_the_adif_contest_id_is_the_cabrillo_name(monkeypatch):
    """ADIF's CONTEST_ID is the Cabrillo name unless a contest overrides it.

    ADIF wants the sponsor's contest id, which is the Cabrillo name for every
    contest we have; ADIFContestID stays as an override, but none sets it.
    """
    seen = []
    monkeypatch.setattr(
        contest,
        "gen_adif",
        lambda parent, cabrillo_name, contest_id: seen.append(contest_id),
    )
    for identifier in ("CQ-WPX-CW", "MWC", "ARI-DX", "10_10_fall_cw"):
        seen.clear()
        loaded = contest.load_contest(identifier, None)
        loaded.adif()
        assert seen == [loaded.CabrilloName]

    loaded = contest.load_contest("CQ-WPX-CW", None)
    loaded.ADIFContestID = "SOMETHING-ELSE"
    seen.clear()
    loaded.adif()
    assert seen == ["SOMETHING-ELSE"]


def test_a_picker_entry_maps_to_an_identifier():
    # The picker's labels are not the contests' display names: "OK1WC" is the
    # label for the contest that calls itself "OK1WC Memorial Contest (MWC)".
    assert contest.contest_identifier_for_display("OK1WC") == "MWC"
    # The fall and spring Ten-Ten sprints share the Cabrillo name 10-10-SPRINT
    # and name themselves, so the label resolves to that name.
    assert contest.contest_identifier_for_display("10 10 FALL CW") == "10_10_fall_cw"
    assert (
        contest.contest_identifier_for_display("10 10 SPRING CW") == "10_10_spring_cw"
    )
    # A display name works too, for callers that have one.
    assert contest.contest_identifier_for_display("CQ WPX CW") == "CQ-WPX-CW"
    assert contest.contest_identifier_for_display("nonsense") is None
