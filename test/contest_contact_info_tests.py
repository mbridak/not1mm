"""The contest's answer about a call: where it is, and what it is worth.

``contact_info()`` is what the call field, the rotator and (later) the bandmap
ask.  It recalls the fields -- from a previous QSO, the call history and
cty.dat -- and then asks the contest's own rules about the dupe and the
multipliers.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from not1mm.lib import contact_info, plugin_common
from not1mm.lib.contact_info import ContactInfo, MultInfo, bearing_to

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


def loaded(case_id, headless, monkeypatch, **pref):
    """A harness with the fixture imported and scored, in its own directory."""
    case = CASES[case_id]
    home = headless / f"{case.contest}-{case.name}"
    home.mkdir(parents=True, exist_ok=True)
    harness = ContestHarness(case.contest, case, home, monkeypatch)
    harness.pref.update(pref)
    plugin_common.import_adif(harness)
    harness.score_log()
    return harness


def test_bearing_prefers_a_real_grid():
    """A grid gives the bearing; without one the entity centre does."""
    beam, kilometers = bearing_to("FN31", "JO01")
    assert 0 <= beam < 360
    assert kilometers > 4000
    centre, _ = bearing_to("FN31", "", 51.5, -0.1)
    assert 0 <= centre < 360
    assert bearing_to("", "JO01") == (None, None)
    assert bearing_to("FN31", "", None, None) == (None, None)


def test_contact_info_for_a_converted_contest(headless, monkeypatch):
    """A declared multiplier is answered from the call alone."""
    contest = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch).contest
    info = contest.contact_info("K5ABC", band=14.0, mode="CW")
    assert isinstance(info, ContactInfo)
    assert (info.prefix, info.continent) == ("K", "NA")
    assert info.beam is not None
    assert info.is_dupe is False
    assert info.mults == (
        MultInfo(name="WPXPrefix", type="wpxprefix", value="K5", is_new=True),
    )


def test_contact_info_from_the_callsign_for_ok1wc(headless, monkeypatch):
    """OK1WC's multiplier is the last letter of the callsign."""
    contest = loaded("ok1wc/K6GTE", headless, monkeypatch).contest
    info = contest.contact_info("OK2ABC", band=7.0, mode="CW")
    assert info.mults[0].value == "C"
    assert info.mults[0].type == "wpxprefix"


def test_contact_info_knows_a_dupe(headless, monkeypatch):
    """A call already in the log is a dupe on the band it was worked on."""
    harness = loaded("ok1wc/K6GTE", headless, monkeypatch)
    existing = harness.database.fetch_all_contacts_asc()[0]
    info = harness.contest.contact_info(
        existing["Call"], band=existing["Band"], mode=existing["Mode"]
    )
    assert info.is_dupe is True


def test_zone_follows_the_zone_type(headless, monkeypatch):
    """ZoneType picks which zone the contest exchanges (UDC)."""
    iaru = loaded("iaru_hf/K6GTE", headless, monkeypatch).contest
    info = iaru.contact_info("JA1ABC", band=14.0, mode="CW")
    assert info.zone == info.itu_zone
    assert info.zone != info.cq_zone

    cq = loaded("cq_ww_cw/K6GTE", headless, monkeypatch).contest
    info = cq.contact_info("K5ABC", band=14.0, mode="CW")
    assert info.zone == info.cq_zone


def test_legacy_contest_has_no_declared_mults(headless, monkeypatch):
    """An unconverted plugin answers the country and the dupe, but no mults."""
    contest = loaded("naqp_cw/K6GTE", headless, monkeypatch).contest
    info = contest.contact_info("K5ABC", band=14.0, mode="CW")
    assert info.prefix == "K"
    assert info.mults == ()


def test_call_history_supplies_a_grid(headless, monkeypatch):
    """The recalled grid is used for the bearing when there is one."""
    harness = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch, use_call_history=True)
    harness.database.exec_sql_insert(
        "CALLHISTORY",
        {"Call": "K5ABC", "Loc1": "EM12", "Sect": "NTX", "Exch1": "5"},
    )
    info = harness.contest.contact_info("K5ABC", band=14.0, mode="CW")
    assert info.grid == "EM12"
    assert info.beam is not None


def test_build_without_a_contest(headless, monkeypatch):
    """With no contest loaded there is still the country and the bearing."""
    harness = loaded("cq_wpx_cw/K6GTE", headless, monkeypatch)
    info = contact_info.build(harness, None, "K5ABC", band=14.0, mode="CW")
    assert info.prefix == "K"
    assert info.beam is not None
    assert info.is_dupe is False
    assert info.mults == ()
