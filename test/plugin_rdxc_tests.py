"""Tests for the Russian DX Contest (RDXC) plugin."""

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from not1mm.plugins import rdxc

CTY = {
    "K6GTE": {"entity": "United States", "continent": "NA", "primary_pfx": "K"},
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


def _make_ctx(contact=None, is_dupe=0, station_call="K6GTE", all_contacts=None):
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
    ctx.database.fetch_all_contacts_asc.return_value = list(all_contacts or [])
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
        # rule 9 keys on the DXCC entity list, where European Russia and
        # Asiatic Russia are separate countries, as is Kaliningrad
        ("UA", "UA"),
        ("UA9", "UA9"),
        ("ua9", "UA9"),
        ("UA2", "UA2"),
        ("K", "K"),
        ("W", "W"),
        ("DL", "DL"),
    ],
)
def test_country_mult_prefix(prefix, expected):
    assert rdxc.country_mult_prefix(prefix) == expected


@pytest.mark.parametrize(
    "prefix,call,expected",
    [
        ("UA", "UA3ABC", True),
        ("UA9", "UA9ABC", True),
        ("UA2", "UA2F", True),  # Kaliningrad
        ("R1FJ", "R1FJ", True),  # Franz Josef Land, rule 7.3
        ("CE9", "RI1AN", True),  # Russian Antarctic, rule 7.3
        ("K", "K6GTE", False),
        ("CE9", "CE9ABC", False),  # Chilean Antarctic is not Russian
        ("", "DL1ABC", False),
    ],
)
def test_is_russian_station(prefix, call, expected):
    assert rdxc.is_russian_station(prefix, call) is expected


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
    ctx = _make_ctx(contact={"Call": "UA3ABC"}, station_call="K6GTE")
    assert rdxc.points(ctx) == 10


def test_points_same_country_is_two():
    ctx = _make_ctx(contact={"Call": "W1AW"}, station_call="K6GTE")
    assert rdxc.points(ctx) == 2


def test_points_different_continent_is_five():
    ctx = _make_ctx(contact={"Call": "DL1ABC"}, station_call="K6GTE")
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
    ctx = _make_entry_ctx(contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"})
    ctx.database.exec_sql.return_value = {"mult_count": 0}
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 1


def test_set_contact_vars_skips_known_oblast():
    ctx = _make_entry_ctx(contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"})
    ctx.database.exec_sql.return_value = {"mult_count": 3}
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 0


def test_set_contact_vars_marks_new_country_mult():
    ctx = _make_entry_ctx(contact={"CountryPrefix": "DL", "Band": 20, "Call": "DL1ABC"})
    ctx.database.exec_sql_mult.return_value = [
        {"CountryPrefix": "K"},
        {"CountryPrefix": "UA9"},
    ]
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 1


def test_set_contact_vars_ua_and_ua9_are_separate_country_mults():
    """Rule 9 uses the DXCC list: European and Asiatic Russia differ."""
    ctx = _make_entry_ctx(contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"})
    ctx.database.exec_sql_mult.return_value = [{"CountryPrefix": "UA9"}]
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 1


def test_set_contact_vars_mm_skipped_for_country_mult():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "K", "Band": 20, "Call": "K6GTE/MM"}
    )
    rdxc.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier2"] == 0
    ctx.database.exec_sql_mult.assert_not_called()


# UA and UA9 are separate countries; R1FJ is Franz Josef Land, whose oblast
# counts under rule 7.3. Three oblasts (MO, SV, AR), four countries.
MULT_CONTACTS = [
    {"Call": "RA3AAA", "CountryPrefix": "UA", "NR": "MO", "Band": 14.0},
    {"Call": "UA9ABC", "CountryPrefix": "UA9", "NR": "SV", "Band": 14.0},
    {"Call": "R1FJ", "CountryPrefix": "R1FJ", "NR": "AR", "Band": 14.0},
    {"Call": "DL1ABC", "CountryPrefix": "DL", "NR": "", "Band": 14.0},
]


def test_show_mults_sums_oblast_and_country():
    ctx = _make_ctx(all_contacts=MULT_CONTACTS)
    assert rdxc.show_mults(ctx) == 7


def test_show_mults_rtc_tuple():
    """RTC tuple follows repo convention: (country, oblast)."""
    ctx = _make_ctx(all_contacts=MULT_CONTACTS)
    assert rdxc.show_mults(ctx, rtc=True) == (4, 3)


def test_show_mults_zero_when_no_rows():
    ctx = _make_ctx(all_contacts=[])
    assert rdxc.show_mults(ctx) == 0


def test_show_mults_counts_per_band_and_skips_mm():
    """Both multipliers are per band, and rule 7.4 gives /MM neither."""
    ctx = _make_ctx(
        all_contacts=[
            {"Call": "RA3AAA", "CountryPrefix": "UA", "NR": "MO", "Band": 14.0},
            {"Call": "RA3AAA", "CountryPrefix": "UA", "NR": "MO", "Band": 7.0},
            {"Call": "UA3ABC/MM", "CountryPrefix": "UA", "NR": "MM", "Band": 14.0},
        ]
    )
    assert rdxc.oblast_multipliers(ctx) == 2
    assert rdxc.country_multipliers(ctx) == 2


def test_rule_7_3_specials_get_both_multipliers():
    """UA2F, RI1FJ and RI1AN are separate countries *and* separate oblasts."""
    ctx = _make_ctx(
        all_contacts=[
            {"Call": "UA2F", "CountryPrefix": "UA2", "NR": "KA", "Band": 14.0},
            {"Call": "R1FJ", "CountryPrefix": "R1FJ", "NR": "AR", "Band": 14.0},
            {"Call": "RI1AN", "CountryPrefix": "CE9", "NR": "AN", "Band": 14.0},
        ]
    )
    assert rdxc.oblast_multipliers(ctx) == 3
    assert rdxc.country_multipliers(ctx) == 3


def test_calc_score_multiplies_points_by_mults():
    ctx = _make_ctx(all_contacts=MULT_CONTACTS)
    ctx.database.fetch_points.return_value = {"Points": "42"}
    assert rdxc.calc_score(ctx) == 294


def test_calc_score_handles_none_points():
    ctx = _make_ctx(all_contacts=MULT_CONTACTS)
    ctx.database.fetch_points.return_value = {"Points": None}
    assert rdxc.calc_score(ctx) == 0


def test_get_mults_shape():
    ctx = _make_ctx(all_contacts=MULT_CONTACTS)
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
        "StationPrefix": "K6GTE",
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
