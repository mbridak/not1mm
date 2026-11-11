"""The base class's scoring machinery: the dupe question and the multipliers.

The corpus in ``contest_logs_test.py`` checks the numbers a contest produces;
this checks the machinery underneath them -- that a dupe is answered from the
declared ``DupeType``, that a multiplier is counted from the declared type
rather than by hand, and that a key can be read off a bandmap spot.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from not1mm.lib import plugin_common
from not1mm.lib.contest import contest_metadata

from contest_harness import ContestHarness, DummyProgress, discover_cases

CASES = {case.id: case for case in discover_cases()}


@pytest.fixture
def headless(monkeypatch, tmp_path):
    """Neutralise plugin_common's Qt bits, as the corpus runner does."""
    monkeypatch.setattr(plugin_common, "QProgressDialog", DummyProgress)
    monkeypatch.setattr(
        plugin_common.QCoreApplication, "processEvents", staticmethod(lambda: None)
    )
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return tmp_path


def loaded(case_id, headless, monkeypatch):
    """A harness with the fixture imported and scored, in its own directory."""
    case = CASES[case_id]
    home = headless / f"{case.contest}-{case.name}"
    home.mkdir(parents=True, exist_ok=True)
    harness = ContestHarness(case.contest, case, home, monkeypatch)
    plugin_common.import_adif(harness)
    harness.score_log()
    return harness


def test_points_per_contact(headless, monkeypatch):
    """OK1WC scores one point a contact, and nothing for a dupe."""
    contest = loaded("ok1wc/K6GTE", headless, monkeypatch).contest
    assert contest.PointsPerContact == 1
    contest.parent.contact_is_dupe = 0
    assert contest.points() == 1
    contest.parent.contact_is_dupe = 1
    assert contest.points() == 0


def test_multiplier_is_declared_not_hand_counted(headless, monkeypatch):
    """The count comes from the declared type and how it is counted per."""
    wpx = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch).contest
    assert (wpx.MultSqlString, wpx.IsMult1Per) == ("WPXPrefix", 4)
    assert wpx.mult_sql(1) == "WPXPrefix"
    assert wpx._mult_columns(1) == ()
    assert wpx.show_mults() == 6
    assert wpx.get_mults() == {"wpxprefix": 6}

    ok1wc = loaded("ok1wc/K6GTE", headless, monkeypatch).contest
    assert (ok1wc.MultSqlString, ok1wc.IsMult1Per) == ("LASTLETTER", 1)
    assert ok1wc.mult_sql(1) == "substr(Call,-1)"
    assert ok1wc._mult_columns(1) == ("Band",)
    assert ok1wc.get_mults() == {"wpxprefix": 6}

    wag = loaded("wag/DL1ABC", headless, monkeypatch).contest
    assert (wag.MultSqlString, wag.IsMult1Per) == ("CountryPrefix", 3)
    assert wag.get_mults() == {"country": 9}


def test_mult_count_reproduces_the_hand_written_helper(headless, monkeypatch):
    """The parameterised query gives what fetch_band_lastletter_count did."""
    harness = loaded("ok1wc/K6GTE", headless, monkeypatch)
    assert (
        harness.database.fetch_mult_key_count("substr(Call,-1)", ("Band",))["count"]
        == harness.database.fetch_band_lastletter_count()["count"]
    )


def test_mult_value_works_from_a_spot(headless, monkeypatch):
    """A bandmap spot carries only a call; a call-derived key still answers."""
    wpx = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch).contest
    assert wpx.mult_value(1, {"WPXPrefix": "K5"}) == "K5"

    ok1wc = loaded("ok1wc/K6GTE", headless, monkeypatch).contest
    assert ok1wc.mult_value(1, {"Call": "OK2ABC"}) == "C"
    assert ok1wc.mult_value(1, {"Call": ""}) == ""


def test_wag_multiplier_depends_on_which_side_you_are_on(headless, monkeypatch):
    """A DL station counts DXCC entities; an outsider counts DOK districts."""
    dl = loaded("wag/DL1ABC", headless, monkeypatch).contest
    assert dl.is_german is True
    assert dl.mult_value(1, {"CountryPrefix": "DL", "NR": "C25"}) == "DL"

    outside = loaded("wag/K6GTE", headless, monkeypatch).contest
    assert outside.is_german is False
    # A special DOK is counted by its first letter, not its first character.
    assert outside.mult_value(1, {"CountryPrefix": "DL", "NR": "60CHILD"}) == "C"
    assert outside.mult_value(1, {"CountryPrefix": "DL", "NR": "NM"}) is None
    assert outside.mult_value(1, {"CountryPrefix": "OK", "NR": "123"}) is None


def test_is_dupe_honours_dupe_type(headless, monkeypatch):
    """DupeType 1/2/3/4 answer all bands / per band / per band+mode / never."""
    harness = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch)
    contest = harness.contest
    first = harness.database.fetch_all_contacts_asc()[0]
    call, band, mode = first["Call"], first["Band"], first["Mode"]

    contest.DupeType = 1
    assert contest.is_dupe(call, band + 1, "SSB") is True
    contest.DupeType = 2
    assert contest.is_dupe(call, band, "SSB") is True
    assert contest.is_dupe(call, band + 1, mode) is False
    contest.DupeType = 3
    assert contest.is_dupe(call, band, mode) is True
    assert contest.is_dupe(call, band, "SSB") is False
    contest.DupeType = 4
    assert contest.is_dupe(call, band, mode) is False


def test_calc_score_is_points_times_mults(headless, monkeypatch):
    """The base's score is the log's points, times the declared multipliers."""
    harness = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch)
    contest = harness.contest
    points = harness.database.fetch_points()["Points"]
    assert contest.calc_score() == points * contest.show_mults()


def test_fixtures_stay_within_the_declared_bands(headless, monkeypatch):
    """A contest that declares its bands must not be handed a log off them."""
    checked = 0
    for case in CASES.values():
        bands = getattr(contest_metadata(case.contest), "Bands", ())
        if not bands:
            continue  # an unconverted plugin does not declare any
        home = headless / f"bands-{case.contest}-{case.name}"
        home.mkdir(parents=True, exist_ok=True)
        harness = ContestHarness(case.contest, case, home, monkeypatch)
        plugin_common.import_adif(harness)
        used = {contact.get("Band") for contact in harness.database.fetch_all_contacts_asc()}
        assert used <= set(bands), (
            f"{case.id}: bands {sorted(used - set(bands))} are not declared"
        )
        checked += 1
    assert checked >= 5, "the converted contests should have been checked"
