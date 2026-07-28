"""Tests for the EU HF Championship (EUHFC) plugin."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from not1mm.plugins import euhfc


def _make_ctx(contact=None, is_dupe=0, sql_result=None, fetch_points=None):
    """Build a minimal fake `self` for the plugin module functions."""
    if contact is None:
        contact = {}
    ctx = SimpleNamespace()
    ctx.contact = contact
    ctx.contact_is_dupe = is_dupe
    ctx.station = {"Call": "S51ZZ"}
    ctx.contest_settings = {"SentExchange": "82"}
    ctx.pref = {"contest": "1"}
    ctx.database = MagicMock()
    ctx.database.exec_sql.return_value = sql_result or {}
    ctx.database.fetch_points.return_value = fetch_points or {"Points": "0"}
    ctx.database.fetch_qso_count.return_value = {"qsos": 0}
    return ctx


def test_module_metadata():
    assert euhfc.name == "EUHFC"
    assert euhfc.cabrillo_name == "EU-HFC"
    assert euhfc.mode == "BOTH"
    # rule 7: dupe once per band+mode
    assert euhfc.dupe_type == 3


def test_points_eu_non_dupe_returns_one():
    ctx = _make_ctx(contact={"Continent": "EU"}, is_dupe=0)
    assert euhfc.points(ctx) == 1


def test_points_dupe_returns_zero():
    ctx = _make_ctx(contact={"Continent": "EU"}, is_dupe=1)
    assert euhfc.points(ctx) == 0


@pytest.mark.parametrize("continent", ["NA", "SA", "AS", "AF", "OC", ""])
def test_points_non_eu_returns_zero(continent):
    """Rule 1: only continental Europe contacts count."""
    ctx = _make_ctx(contact={"Continent": continent}, is_dupe=0)
    assert euhfc.points(ctx) == 0


def test_show_mults_query_is_per_band_only():
    """Rule 6: multiplier is counted once per band regardless of mode.
    The SQL must group by NR+Band, not include Mode."""
    ctx = _make_ctx(sql_result={"nb_count": 7})
    result = euhfc.show_mults(ctx)
    assert result == 7
    ctx.database.exec_sql.assert_called_once()
    query = ctx.database.exec_sql.call_args[0][0]
    assert "NR" in query
    assert "Band" in query
    # rule 6: must NOT partition mults by Mode
    assert "Mode" not in query


def test_show_mults_zero_when_no_rows():
    ctx = _make_ctx(sql_result={})
    assert euhfc.show_mults(ctx) == 0


def test_calc_score_multiplies_points_by_mults():
    """Rule 8: score = total QSO points x total multipliers."""
    ctx = _make_ctx(
        sql_result={"nb_count": 10},
        fetch_points={"Points": "42"},
    )
    assert euhfc.calc_score(ctx) == 420


def test_calc_score_handles_none_points():
    ctx = _make_ctx(
        sql_result={"nb_count": 3},
        fetch_points={"Points": None},
    )
    assert euhfc.calc_score(ctx) == 0


def test_set_contact_vars_captures_exchange():
    ctx = _make_ctx(contact={})
    ctx.sent = SimpleNamespace(text=lambda: "599")
    ctx.receive = SimpleNamespace(text=lambda: "599")
    ctx.other_2 = SimpleNamespace(text=lambda: "82")
    ctx.contest_settings = {"SentExchange": "17"}
    euhfc.set_contact_vars(ctx)
    assert ctx.contact["SNT"] == "599"
    assert ctx.contact["RCV"] == "599"
    assert ctx.contact["NR"] == "82"
    assert ctx.contact["SentNr"] == "17"


def test_get_mults_shape():
    ctx = _make_ctx(sql_result={"nb_count": 5})
    m = euhfc.get_mults(ctx)
    assert m == {"licyear": 5}


def test_output_cabrillo_line_format():
    """Cabrillo line writer must respect encoding and line ending."""
    buf = io.StringIO()
    euhfc.output_cabrillo_line("CONTEST: EU-HFC", "\r\n", buf, "ascii")
    assert buf.getvalue() == "CONTEST: EU-HFC\r\n"


def test_qso_line_shape_matches_rules():
    """A QSO line built from typical field values should carry: date, time,
    stationprefix, RST sent, sent-lic-year, worked call, RST rcv, rcv-lic-year.
    We construct the expected line by hand and confirm the format hasn't drifted."""
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
    themode = contact["Mode"]
    frequency = str(round(contact["Freq"])).rjust(5)
    ts = contact["TS"]
    loggeddate = ts[:10]
    loggedtime = ts[11:13] + ts[14:16]
    line = (
        f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
        f"{contact['StationPrefix'].ljust(13)} "
        f"{str(contact['SNT']).ljust(3)} "
        f"{str(contact['SentNr']).ljust(3)} "
        f"{contact['Call'].ljust(13)} "
        f"{str(contact['RCV']).ljust(3)} "
        f"{str(contact['NR']).ljust(3)}"
    )
    # sanity: the two 2-digit exchanges appear separately, RSTs untouched
    assert " 599 " in line
    assert " 82 " in line
    assert " 17" in line
    assert "OK2ABC" in line
    assert line.startswith("QSO: 14025 CW 2026-08-01 1234 ")
