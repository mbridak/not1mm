"""Tests for the Russian DX Contest (RDXC) plugin.

Reference:
  https://www.rdxc.org/rules_eng  (rules 7, 9)
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from contest_harness import ContestHarness, DummyProgress, discover_cases

from not1mm.lib import plugin_common
from not1mm.lib.contest import load_contest
from not1mm.plugins import rdxc
from not1mm.plugins.rdxc import Contest

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


def _make_ctx(contact=None, is_dupe=0, station_call="K6GTE"):
    """Build a minimal fake main window for points()."""
    if contact is None:
        contact = {}
    return SimpleNamespace(
        contact=contact,
        contact_is_dupe=is_dupe,
        station={"Call": station_call},
        contest_settings={"SentExchange": "001"},
        pref={"contest": "1"},
        cty_lookup=_fake_cty,
    )


class FakeLineEdit:
    """Stands in for a QLineEdit."""

    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text


class FakeDatabase:
    """Just enough DataBase for set_contact_vars()."""

    def __init__(self, seen=()):
        self.seen = set(seen)
        self.lookups = 0

    def mult_key_exists(self, expression, value, per=(), band=None, mode=None):
        self.lookups += 1
        return {"count": 1 if (value, band) in self.seen else 0}


def _make_entry_ctx(contact=None, is_dupe=0, seen=()):
    """Add the entry widgets and the multiplier lookup set."""
    if contact is None:
        contact = {}
    ctx = _make_ctx(contact=contact, is_dupe=is_dupe)
    ctx.sent = FakeLineEdit("599")
    ctx.receive = FakeLineEdit("599")
    ctx.other_1 = FakeLineEdit("001")
    ctx.other_2 = FakeLineEdit("mos")
    ctx.database = FakeDatabase(seen)
    return ctx


def test_class_metadata():
    assert Contest.DisplayName == "RDXC"
    assert Contest.CabrilloName == "RDXC"
    assert Contest.Mode == "BOTH"
    # rule: once per band per mode
    assert Contest.DupeType == 3
    assert Contest.EXCHANGE_HINT == "# or Oblast"


def test_log_columns_shape():
    assert Contest.LogInfo[0] == "YYYY-MM-DD HH:MM:SS"
    assert "SentNr" in Contest.LogInfo
    assert "RcvNr" in Contest.LogInfo
    assert "NR" not in Contest.LogInfo
    assert Contest.LogInfo[-3:] == ["M1", "M2", "PTS"]


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
    assert load_contest("rdxc", ctx).points() == 0


def test_points_mm_returns_five():
    ctx = _make_ctx(contact={"Call": "DL1ABC/MM"}, is_dupe=0)
    assert load_contest("rdxc", ctx).points() == 5


def test_points_unresolvable_call_returns_zero():
    ctx = _make_ctx(contact={"Call": "ZZ9ZZZ"}, is_dupe=0)
    assert load_contest("rdxc", ctx).points() == 0


@pytest.mark.parametrize(
    "his_call,my_call,expected",
    [
        ("UA3ABC", "K6GTE", 10),  # non-Russian to Russia
        ("W1AW", "K6GTE", 2),  # same country
        ("DL1ABC", "K6GTE", 5),  # different continent
        ("UA3ABC", "RA3AAA", 2),  # Russia on the same continent
        ("UA9ABC", "UA3ABC", 5),  # Russia on another continent
        ("DL1ABC", "RA3AAA", 3),  # another country on the same continent
        ("JA1ABC", "UA3ABC", 5),  # another continent
        ("UA3ABC", "UA2F", 2),  # Kaliningrad counts as Russian
    ],
)
def test_points(his_call, my_call, expected):
    ctx = _make_ctx(contact={"Call": his_call}, station_call=my_call)
    assert load_contest("rdxc", ctx).points() == expected


def test_set_contact_vars_captures_exchange():
    ctx = _make_entry_ctx()
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["SNT"] == "599"
    assert ctx.contact["RCV"] == "599"
    assert ctx.contact["SentNr"] == "001"
    assert ctx.contact["NR"] == "MOS"


def test_set_contact_vars_dupe_does_not_mark_mult():
    ctx = _make_entry_ctx(is_dupe=1)
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier1"] == 0
    assert ctx.contact["IsMultiplier2"] == 0
    assert ctx.database.lookups == 0


def test_set_contact_vars_marks_new_oblast_mult():
    ctx = _make_entry_ctx(contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"})
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier1"] == 1


def test_set_contact_vars_skips_known_oblast():
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"},
        seen=[("MOS", 20)],
    )
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier1"] == 0


def test_set_contact_vars_marks_new_country_mult():
    ctx = _make_entry_ctx(contact={"CountryPrefix": "DL", "Band": 20, "Call": "DL1ABC"})
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier2"] == 1


def test_set_contact_vars_ua_and_ua9_are_separate_country_mults():
    """Rule 9 uses the DXCC list: European and Asiatic Russia differ."""
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "UA", "Band": 20, "Call": "UA3ABC"},
        seen=[("UA9", 20)],
    )
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier2"] == 1


def test_set_contact_vars_mm_skipped_for_country_mult():
    """Rule 7.4: a maritime-mobile contact is no multiplier at all."""
    ctx = _make_entry_ctx(
        contact={"CountryPrefix": "K", "Band": 20, "Call": "K6GTE/MM"}
    )
    load_contest("rdxc", ctx).set_contact_vars()
    assert ctx.contact["IsMultiplier1"] == 0
    assert ctx.contact["IsMultiplier2"] == 0


@pytest.mark.parametrize(
    "contact,expected",
    [
        # a Russian station's oblast, from the country prefix or rule 7.3
        ({"Call": "UA3ABC", "CountryPrefix": "UA", "NR": "MO"}, "MO"),
        ({"Call": "R1FJ", "CountryPrefix": "R1FJ", "NR": "AR"}, "AR"),
        ({"Call": "RI1AN", "CountryPrefix": "CE9", "NR": "AN"}, "AN"),
        ({"Call": "UA3ABC", "CountryPrefix": "UA", "NR": ""}, None),
        # a serial from anywhere else is not an oblast
        ({"Call": "DL1ABC", "CountryPrefix": "DL", "NR": "001"}, None),
        # rule 7.4
        ({"Call": "UA3ABC/MM", "CountryPrefix": "UA", "NR": "MM"}, None),
    ],
)
def test_oblast_multiplier_key(contact, expected):
    assert load_contest("rdxc", SimpleNamespace()).mult_value(1, contact) == expected


@pytest.mark.parametrize(
    "contact,expected",
    [
        ({"Call": "DL1ABC", "CountryPrefix": "DL"}, "DL"),
        ({"Call": "UA9ABC", "CountryPrefix": "UA9"}, "UA9"),
        ({"Call": "K6GTE/MM", "CountryPrefix": "K"}, None),
    ],
)
def test_country_multiplier_key(contact, expected):
    assert load_contest("rdxc", SimpleNamespace()).mult_value(2, contact) == expected


def test_the_oblast_key_falls_back_to_cty():
    """An imported log without COUNTRYPREFIX still answers the oblast key."""
    ctx = SimpleNamespace(cty_lookup=_fake_cty)
    contact = {"Call": "UA3ABC", "NR": "MO"}
    assert load_contest("rdxc", ctx).mult_value(1, contact) == "MO"


def test_both_multipliers_are_counted_per_band():
    contest = load_contest("rdxc", SimpleNamespace())
    assert contest._mult_columns(1) == ("Band",)
    assert contest._mult_columns(2) == ("Band",)


def test_sql_keys_agree_with_the_python_ones():
    contest = load_contest("rdxc", SimpleNamespace())
    oblast = contest.mult_sql(1)
    assert "NR <> ''" in oblast
    assert "CountryPrefix IN ('UA', 'UA9', 'UA2')" in oblast
    assert "Call LIKE 'R1FJ%'" in oblast
    assert "%/MM%" in oblast
    country = contest.mult_sql(2)
    assert country == "CASE WHEN Call NOT LIKE '%/MM%' THEN CountryPrefix END"


# -- the numbers the K6GTE corpus case produces --------------------------------
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


@pytest.fixture
def k6gte(headless, monkeypatch):
    case = CASES["rdxc/K6GTE"]
    home = headless / f"{case.contest}-{case.name}"
    home.mkdir(parents=True, exist_ok=True)
    harness = ContestHarness(case.contest, case, home, monkeypatch)
    plugin_common.import_adif(harness)
    harness.score_log()
    return harness


def test_show_mults_sums_oblast_and_country(k6gte):
    assert k6gte.contest.show_mults() == 13


def test_show_mults_counts_each_oblast_once_per_band(k6gte):
    """RA3AAA/MO is worked on 20m twice and once on 40m: two multipliers."""
    assert k6gte.contest._mult_count(1) == 5
    assert k6gte.contest._mult_count(2) == 8


def test_get_mults_shape(k6gte):
    assert k6gte.contest.get_mults() == {"country": 8, "oblast": 5}


def test_calc_score_multiplies_points_by_mults(k6gte):
    assert k6gte.contest.calc_score() == 871


def test_prefill_sets_zero_padded_serial():
    ctx = _make_ctx()
    ctx.current_sn = 12
    ctx.other_1 = FakeLineEdit("")
    load_contest("rdxc", ctx).prefill()
    assert ctx.other_1.text() == "012"


def test_prefill_sets_001_when_there_is_no_serial():
    ctx = _make_ctx()
    ctx.current_sn = None
    ctx.other_1 = FakeLineEdit("")
    load_contest("rdxc", ctx).prefill()
    assert ctx.other_1.text() == "001"


def test_prefill_keeps_existing_value():
    ctx = _make_ctx()
    ctx.current_sn = 12
    ctx.other_1 = MagicMock()
    ctx.other_1.text.return_value = "005"
    load_contest("rdxc", ctx).prefill()
    ctx.other_1.setText.assert_not_called()


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
    line = Contest(None).cabrillo_qso_line(contact)
    assert line == (
        "QSO: 14025 CW 2026-03-21 1015 K6GTE         599 001    "
        "UA3ABC        599 MOS   "
    )


def test_qso_line_writes_rtty_as_ry():
    contact = {
        "TS": "2026-03-21 10:15:30",
        "Mode": "RTTY",
        "Freq": 14025.0,
        "StationPrefix": "K6GTE",
        "SNT": "599",
        "SentNr": "001",
        "Call": "UA3ABC",
        "RCV": "599",
        "NR": "MOS",
    }
    assert " RY " in Contest(None).cabrillo_qso_line(contact)
