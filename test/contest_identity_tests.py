"""How a contest is named, and how it is found again.

A contest is identified by the stem of the file it is defined in -- its
*basename*: ``not1mm/plugins/<basename>.py`` or ``<basename>.udc``.  That is
the one name two definitions cannot share: the Cabrillo name is not unique
(``QSO_PARTY``, ``10-10-SPRINT``) and neither is a UDC's ``Name``.  The
basename is what ``ContestInstance.ContestName`` stores, so loading a stored
log gets the same contest back, and it is what the contest's directory under
``~/.local/share/not1mm`` is called.

The Cabrillo name is only what the sponsor's log checker sees (``CONTEST:``,
ADIF, the log file name, and the contact rows).  It is not an identifier: a
stored value that is only a Cabrillo name no longer resolves.
"""

from __future__ import annotations

import pytest

from not1mm.lib import contest

FIRST = "cq_wpx_cw"
SECOND = "spdx"


def test_the_id_is_the_basename():
    assert contest.contest_metadata(FIRST).BaseName == FIRST
    assert contest.contest_metadata(SECOND).BaseName == SECOND


def test_two_contests_that_share_a_cabrillo_name_have_distinct_ids():
    # The two templates share the Cabrillo name QSO_PARTY but are not
    # interchangeable; only the file name tells them apart.
    rst = contest.contest_metadata("qso_party_rst")
    sn = contest.contest_metadata("qso_party_sn")
    assert rst.CabrilloName == sn.CabrilloName == "QSO_PARTY"
    assert rst.BaseName == "qso_party_rst"
    assert sn.BaseName == "qso_party_sn"


@pytest.mark.parametrize(
    "asked_for",
    [
        "cq_wpx_cw",  # the basename, which is what the database stores
        "CQ_WPX_CW",  # ... matched without case
    ],
)
def test_a_contest_is_found_by_its_basename(asked_for):
    loaded = contest.load_contest(asked_for, None)
    assert loaded.BaseName == "cq_wpx_cw"
    assert loaded.name == "CQ WPX CW"


def test_only_the_basename_resolves_a_contest():
    # A display or Cabrillo name is not an identifier: the display name is
    # resolved by contest_basename_for_display(), and several contests share
    # a Cabrillo name.
    for not_an_id in ("CQ WPX CW", "CQ-WPX-CW", "MWC"):
        with pytest.raises(ModuleNotFoundError):
            contest.load_contest(not_an_id, None)


def test_an_unknown_contest_is_an_error():
    with pytest.raises(ModuleNotFoundError):
        contest.load_contest("no such contest", None)


def test_a_missing_identifier_is_an_error():
    for nothing in (None, ""):
        with pytest.raises(ModuleNotFoundError):
            contest.load_contest(nothing, None)


def test_an_old_stored_value_still_resolves():
    # Before 0842c5ec the database held the folded file name, e.g. "ok1wc";
    # that is the basename, so it keeps loading.
    assert contest.load_contest("ok1wc", None).BaseName == "ok1wc"
    assert contest.load_contest("cq_wpx_cw", None).BaseName == "cq_wpx_cw"


def test_general_logging_is_available_as_the_fallback():
    # MainWindow.load_contest() opens a stored name it cannot resolve as
    # General Logging, so the contacts stay reachable.
    loaded = contest.load_contest(contest.FALLBACK_BASENAME, None)
    assert loaded.BaseName == "general_logging"
    assert loaded.DisplayName == "General Logging"


def test_every_contest_declares_a_basename():
    available = contest.available_contests()
    from not1mm.lib.parse_udc import udc_files

    assert len(available) == len(contest._contest_basenames()) + len(udc_files())
    assert len({info.basename for info in available}) == len(available)
    for info in available:
        assert info.basename, info.display_name
        assert info.display_name, info.basename
        assert info.cabrillo_name, info.basename
        assert isinstance(info.sort_order, int), info.basename


def test_every_contest_can_be_loaded_by_its_basename():
    for info in contest.available_contests():
        loaded = contest.load_contest(info.basename, None)
        assert loaded.BaseName == info.basename


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
    for basename in ("cq_wpx_cw", "ok1wc", "ari_dx", "10_10_fall_cw"):
        seen.clear()
        loaded = contest.load_contest(basename, None)
        loaded.adif()
        assert seen == [loaded.CabrilloName]

    loaded = contest.load_contest("cq_wpx_cw", None)
    loaded.ADIFContestID = "SOMETHING-ELSE"
    seen.clear()
    loaded.adif()
    assert seen == ["SOMETHING-ELSE"]


def test_a_picker_entry_maps_to_a_basename():
    # The old picker's labels were not the contests' display names: "OK1WC"
    # was the label for the contest that now calls itself "OK1WC Memorial
    # Contest".  The fold over those stored labels has to keep resolving.
    assert contest.contest_basename_for_display("OK1WC") == "ok1wc"
    # The fall and spring Ten-Ten sprints share the Cabrillo name 10-10-SPRINT
    # and are told apart by their file names.
    assert contest.contest_basename_for_display("10 10 FALL CW") == "10_10_fall_cw"
    assert contest.contest_basename_for_display("10 10 SPRING CW") == "10_10_spring_cw"
    # A display name works too, for callers that have one.
    assert contest.contest_basename_for_display("CQ WPX CW") == "cq_wpx_cw"
    assert contest.contest_basename_for_display("nonsense") is None
