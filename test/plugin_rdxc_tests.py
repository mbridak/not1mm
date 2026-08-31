"""Tests for the Russian DX Contest (RDXC) plugin."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from not1mm.plugins import rdxc

CTY = {
    "K5TUX": {"entity": "United States", "continent": "NA", "primary_pfx": "K"},
    "W1AW": {"entity": "United States", "continent": "NA", "primary_pfx": "W"},
    "DL1ABC": {"entity": "Germany", "continent": "EU", "primary_pfx": "DL"},
    "RA3AAA": {"entity": "European Russia", "continent": "EU", "primary_pfx": "UA"},
    "UA3ABC": {"entity": "European Russia", "continent": "EU", "primary_pfx": "UA"},
    "UA9ABC": {"entity": "Asiatic Russia", "continent": "AS", "primary_pfx": "UA9"},
    "UA2F": {"entity": "Kaliningrad", "continent": "EU", "primary_pfx": "UA2"},
    "ZS1ABC": {"entity": "South Africa", "continent": "AF", "primary_pfx": "ZS"},
    "FK1AA": {"entity": "New Caledonia", "continent": "OC", "primary_pfx": "FK"},
    "JA1ABC": {"entity": "Japan", "continent": "AS", "primary_pfx": "JA"},
}


def _fake_cty(call):
    item = CTY.get(call)
    if item is None:
        return None
    return {call: item}


def _make_ctx(contact=None, is_dupe=0, station_call="K5TUX"):
    """Build a minimal fake `self` for the plugin module functions."""
    if contact is None:
        contact = {}
    ctx = SimpleNamespace()
    ctx.contact = contact
    ctx.contact_is_dupe = is_dupe
    ctx.station = {"Call": station_call}
    ctx.contest_settings = {"SentExchange": "001"}
    ctx.pref = {"contest": "1"}
    ctx.cty_lookup = _fake_cty
    ctx.database = MagicMock()
    ctx.database.exec_sql.return_value = {}
    ctx.database.exec_sql_mult.return_value = []
    ctx.database.fetch_points.return_value = {"Points": "0"}
    ctx.database.fetch_qso_count.return_value = {"qsos": 0}
    return ctx


def _make_entry_ctx(contact=None, is_dupe=0):
    """Add the entry widgets used by set_contact_vars."""
    ctx = _make_ctx(contact=contact, is_dupe=is_dupe)
    ctx.sent = SimpleNamespace(text=lambda: "599")
    ctx.receive = SimpleNamespace(text=lambda: "599")
    ctx.other_1 = SimpleNamespace(text=lambda: "001")
    ctx.other_2 = SimpleNamespace(text=lambda: "mos")
    return ctx


def test_module_metadata():
    assert rdxc.name == "RDXC"
    assert rdxc.cabrillo_name == "RDXC"
    assert rdxc.mode == "BOTH"
    # rule: once per band per mode
    assert rdxc.dupe_type == 3
    assert rdxc.EXCHANGE_HINT == "# or Oblast"


def test_columns_shape():
    assert rdxc.columns[0] == "YYYY-MM-DD HH:MM:SS"
    assert "SentNr" in rdxc.columns
    assert "RcvNr" in rdxc.columns
    assert "NR" not in rdxc.columns


@pytest.mark.parametrize("prefix", ["UA", "UA9", "UA2", "ua", "ua9", "ua2"])
def test_is_russian_prefix_true(prefix):
    assert rdxc.is_russian_prefix(prefix)


@pytest.mark.parametrize("prefix", ["K", "W", "DL", "F", "ZS", ""])
def test_is_russian_prefix_false(prefix):
    assert not rdxc.is_russian_prefix(prefix)


@pytest.mark.parametrize(
    "prefix,expected",
    [
        ("UA", "R"),
        ("UA9", "R"),
        ("ua9", "R"),
        ("UA2", "UA2"),
        ("K", "K"),
        ("W", "W"),
        ("DL", "DL"),
    ],
)
def test_country_mult_prefix(prefix, expected):
    assert rdxc.country_mult_prefix(prefix) == expected


def test_points_dupe_returns_zero():
    ctx = _make_ctx(contact={"Call": "DL1ABC"}, is_dupe=1)
    assert rdxc.points(ctx) == 0


def test_points_mm_returns_five():
    ctx = _make_ctx(contact={"Call": "DL1ABC/MM"}, is_dupe=0)
    assert rdxc.points(ctx) == 5


def test_points_unresolvable_call_returns_zero():
    ctx = _make_ctx(contact={"Call": "ZZ9ZZZ"}, is_dupe=0)
    assert rdxc.points(ctx) == 0


def test_points_non_russian_to_russia_is_ten():
    ctx = _make_ctx(contact={"Call": "UA3ABC"}, station_call="K5TUX")
    assert rdxc.points(ctx) == 10


def test_points_same_country_is_two():
    ctx = _make_ctx(contact={"Call": "W1AW"}, station_call="K5TUX")
    assert rdxc.points(ctx) == 2


def test_points_different_continent_is_five():
    ctx = _make_ctx(contact={"Call": "DL1ABC"}, station_call="K5TUX")
    assert rdxc.points(ctx) == 5


def test_points_russian_russia_same_continent_is_two():
    ctx = _make_ctx(contact={"Call": "UA3ABC"}, station_call="RA3AAA")
    assert rdxc.points(ctx) == 2


def test_points_russian_russia_other_continent_is_five():
    ctx = _make_ctx(contact={"Call": "UA9ABC"}, station_call="UA3ABC")
    assert rdxc.points(ctx) == 5


def test_points_russian_same_continent_other_country_is_three():
    ctx = _make_ctx(contact={"Call": "DL1ABC"}, station_call="RA3AAA")
    assert rdxc.points(ctx) == 3


def test_points_russian_other_continent_is_five():
    ctx = _make_ctx(contact={"Call": "JA1ABC"}, station_call="UA3ABC")
    assert rdxc.points(ctx) == 5


def test_points_kaliningrad_counts_as_russian():
    ctx = _make_ctx(contact={"Call": "UA3ABC"}, station_call="UA2F")
    assert rdxc.points(ctx) == 2


def test_set_contact_vars_captures_exchange():
    ctx = _make_entry_ctx()
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["SNT"] == "599"
    assert ctx.contact["RCV"] == "599"
    assert ctx.contact["SentNr"] == "001"
    assert ctx.contact["NR"] == "MOS"


def test_set_contact_vars_dupe_does_not_mark_mult():
    ctx = _make_entry_ctx(is_dupe=1)
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 0
    assert ctx.contact["IsMultiplier2"] == 0


def test_set_contact_vars_marks_new_oblast_mult():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"}
    )
    ctx.database.exec_sql.return_value = {"mult_count": 0}
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 1


def test_set_contact_vars_skips_known_oblast():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"}
    )
    ctx.database.exec_sql.return_value = {"mult_count": 3}
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 0


def test_set_contact_vars_marks_new_country_mult():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "DL", "Band": 20, "Call": "DL1ABC"}
    )
    ctx.database.exec_sql_mult.return_value = [
        {"CountryPrefix": "K"},
        {"CountryPrefix": "UA9"},
    ]
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 1


def test_set_contact_vars_ua_and_ua9_share_country_mult():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"}
    )
    ctx.database.exec_sql_mult.return_value = [{"CountryPrefix": "UA9"}]
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 0


def test_set_contact_vars_mm_skipped_for_country_mult():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "K", "Band": 20, "Call": "K5TUX/MM"}
    )
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 0
    ctx.database.exec_sql_mult.assert_not_called()


def test_show_mults_sums_oblast_and_country():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.exec_sql.side_effect = [{"mult_count": 3}, {"mult_count": 4}]
    assert rdxc.show_mults(ctx) == 7


def test_show_mults_rtc_tuple():
    """RTC tuple follows repo convention: (country, oblast)."""
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.exec_sql.side_effect = [{"mult_count": 3}, {"mult_count": 4}]
    assert rdxc.show_mults(ctx, rtc=True) == (4, 3)


def test_show_mults_zero_when_no_rows():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.exec_sql.return_value = {}
    assert rdxc.show_mults(ctx) == 0


def test_show_mults_queries_split_by_band():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.exec_sql.return_value = {}
    rdxc.show_mults(ctx)
    queries = [call[0][0] for call in ctx.database.exec_sql.call_args_list]
    assert len(queries) == 2
    assert all("Band" in q for q in queries)
    # oblast query is limited to Russian prefixes
    assert "CountryPrefix in ('UA', 'UA9', 'UA2')" in queries[0]
    # country query excludes maritime mobile stations
    assert "not like '%/MM%'" in queries[1]


def test_calc_score_multiplies_points_by_mults():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.fetch_points.return_value = {"Points": "42"}
    ctx.database.exec_sql.side_effect = [{"mult_count": 3}, {"mult_count": 4}]
    assert rdxc.calc_score(ctx) == 294


def test_calc_score_handles_none_points():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.fetch_points.return_value = {"Points": None}
    ctx.database.exec_sql.side_effect = [{"mult_count": 1}, {"mult_count": 1}]
    assert rdxc.calc_score(ctx) == 0


def test_get_mults_shape():
    ctx = _make_ctx()
    ctx.database.current_contest = "1"
    ctx.database.exec_sql.side_effect = [{"mult_count": 3}, {"mult_count": 4}]
    assert rdxc.get_mults(ctx) == {"country": 4, "oblast": 3}


def test_show_qso():
    ctx = _make_ctx()
    ctx.database.fetch_qso_count.return_value = {"qsos": 5}
    assert rdxc.show_qso(ctx) == 5


def test_prefill_sets_zero_padded_serial():
    ctx = _make_ctx()
    ctx.current_sn = 12
    ctx.other_1 = SimpleNamespace(text=lambda: "", setText=MagicMock())
    rdxc.prefill(ctx)
    ctx.other_1.setText.assert_called_once_with("012")


def test_prefill_keeps_existing_value():
    ctx = _make_ctx()
    ctx.current_sn = 12
    ctx.other_1 = SimpleNamespace(text=lambda: "005", setText=MagicMock())
    rdxc.prefill(ctx)
    ctx.other_1.setText.assert_not_called()


def test_output_cabrillo_line_format():
    buf = io.StringIO()
    rdxc.output_cabrillo_line("CONTEST: RDXC", "\r\n", buf, "ascii")
    assert buf.getvalue() == "CONTEST: RDXC\r\n"


def test_qso_line_format():
    contact = {
        "TS": "2026-03-21 10:15:30",
        "Mode": "CW",
        "Freq": 14025.0,
        "StationPrefix": "K5TUX",
        "SNT": "599",
        "SentNr": "001",
        "Call": "UA3ABC",
        "RCV": "599",
        "NR": "MOS",
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
        f"{str(contact['SentNr']).ljust(6)} "
        f"{contact['Call'].ljust(13)} "
        f"{str(contact['RCV']).ljust(3)} "
        f"{str(contact['NR']).ljust(6)}"
    )
    assert " 599 " in line
    assert " 001 " in line
    assert " MOS " in line
    assert "UA3ABC" in line
    assert line.startswith("QSO: 14025 CW 2026-03-21 1015 ")
