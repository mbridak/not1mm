"""Tests for the EU HF Championship (EUHFC) plugin."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from not1mm.lib.contest import load_contest, output_cabrillo_line
from not1mm.plugins.euhfc import Contest


def _make_parent(contact=None, is_dupe=0, mult_count=0, fetch_points=None):
    """Build a minimal fake main window for the plugin class."""
    if contact is None:
        contact = {}
    parent = SimpleNamespace()
    parent.contact = contact
    parent.contact_is_dupe = is_dupe
    parent.station = {"Call": "S51ZZ"}
    parent.contest_settings = {"SentExchange": "82"}
    parent.pref = {"contest": "1"}
    parent.database = MagicMock()
    parent.database.fetch_mult_key_count.return_value = {"count": mult_count}
    parent.database.fetch_points.return_value = fetch_points or {"Points": "0"}
    parent.database.fetch_qso_count.return_value = {"qsos": 0}
    parent.database.mult_key_exists.return_value = {"count": 1}
    return parent


def _contest(**kwargs):
    parent = _make_parent(**kwargs)
    return load_contest("euhfc", parent), parent


def test_class_metadata():
    assert Contest.DisplayName == "EUHFC"
    assert Contest.CabrilloName == "EUHFC"
    assert Contest.Mode == "BOTH"
    # rule 7: dupe once per band+mode
    assert Contest.DupeType == 3


def test_points_eu_non_dupe_returns_one():
    contest, _ = _contest(contact={"Continent": "EU"}, is_dupe=0)
    assert contest.points() == 1


def test_points_dupe_returns_zero():
    contest, _ = _contest(contact={"Continent": "EU"}, is_dupe=1)
    assert contest.points() == 0


@pytest.mark.parametrize("continent", ["NA", "SA", "AS", "AF", "OC", ""])
def test_points_non_eu_returns_zero(continent):
    """Rule 1: only continental Europe contacts count."""
    contest, _ = _contest(contact={"Continent": continent}, is_dupe=0)
    assert contest.points() == 0


def test_show_mults_is_per_band_only():
    """Rule 6: multiplier is counted once per band regardless of mode."""
    assert Contest.MultSqlString == "NR"
    assert Contest.IsMult1Per == 1
    contest, parent = _contest(mult_count=7)
    assert contest.show_mults() == 7
    parent.database.fetch_mult_key_count.assert_called_once()
    expression, per = parent.database.fetch_mult_key_count.call_args[0]
    assert "NR" in expression
    assert per == ("Band",)


def test_show_mults_zero_when_no_rows():
    contest, _ = _contest(mult_count=0)
    assert contest.show_mults() == 0


def test_calc_score_multiplies_points_by_mults():
    """Rule 8: score = total QSO points x total multipliers."""
    contest, _ = _contest(mult_count=10, fetch_points={"Points": "42"})
    assert contest.calc_score() == 420


def test_calc_score_handles_none_points():
    contest, _ = _contest(mult_count=3, fetch_points={"Points": None})
    assert contest.calc_score() == 0


def test_set_contact_vars_captures_exchange():
    contest, parent = _contest(contact={})
    parent.sent = SimpleNamespace(text=lambda: "599")
    parent.receive = SimpleNamespace(text=lambda: "599")
    parent.other_2 = SimpleNamespace(text=lambda: "82")
    parent.contest_settings = {"SentExchange": "17"}
    contest.set_contact_vars()
    assert parent.contact["SNT"] == "599"
    assert parent.contact["RCV"] == "599"
    assert parent.contact["NR"] == "82"
    assert parent.contact["SentNr"] == "17"


def test_get_mults_shape():
    contest, _ = _contest(mult_count=5)
    m = contest.get_mults()
    assert m == {"licyear": 5}


def test_output_cabrillo_line_format():
    """Cabrillo line writer must respect encoding and line ending."""
    buf = io.StringIO()
    output_cabrillo_line("CONTEST: EU-HFC", "\r\n", buf, "ascii")
    assert buf.getvalue() == "CONTEST: EU-HFC\r\n"


def test_qso_line_shape_matches_rules():
    """A QSO line built from typical field values should carry: date, time,
    stationprefix, RST sent, sent-lic-year, worked call, RST rcv, rcv-lic-year,
    with the two-digit years in three columns."""
    contest = load_contest("euhfc", SimpleNamespace())
    contact = {
        "TS": "2026-08-01 12:34:56",
        "Mode": "CW",
        "Freq": 14025.0,
        "StationPrefix": "S51ZZ",
        "SNT": "599",
        "SentNr": "82",
        "Call": "OK2ABC",
        "RCV": "599",
        "NR": "17",
    }
    line = contest.cabrillo_qso_line(contact)
    expected = (
        "QSO: 14025 CW 2026-08-01 1234 "
        "S51ZZ         "
        "599 "
        "82  "
        "OK2ABC        "
        "599 "
        "17 "
    )
    assert line == expected
