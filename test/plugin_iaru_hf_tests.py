"""IARU HF World Championship: the points and the zone/HQ multiplier split.

Reference:
  https://contests.arrl.org/ContestRules/IARU-HF-Rules.pdf  (rules 5.1, 5.2)
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from contest_harness import ContestHarness, DummyProgress, discover_cases

from not1mm.lib import plugin_common
from not1mm.lib.contest import load_contest
from not1mm.plugins.iaru_hf import Contest

_ENTITIES = {
    "K6GTE": ("United States", "NA"),
    "DL1ABC": ("Fed. Rep. of Germany", "EU"),
    "N0AX": ("United States", "NA"),
    "SM5XYZ": ("Sweden", "EU"),
}


def _ctx(zone, zn, continent=None, his_call="N0AX", my_call="K6GTE"):
    def cty(call):
        entity, cont = _ENTITIES[call]
        return {"0": {"entity": entity, "continent": cont}}

    contact = {"ZN": zn, "Call": his_call}
    if continent is not None:
        contact["Continent"] = continent
    return SimpleNamespace(
        contact_is_dupe=0,
        station={"Call": my_call, "IARUZone": zone},
        contact=contact,
        cty_lookup=cty,
    )


@pytest.mark.parametrize(
    "my_call,zone,zn,continent,expected",
    [
        # our own zone is one point
        ("K6GTE", 8, "8", "NA", 1),
        # an HQ station sends a society abbreviation, not a zone: one point
        ("K6GTE", 8, "ARRL", "NA", 1),
        ("DL1ABC", 28, "R1", "EU", 1),
        # another zone on the same continent is three
        ("K6GTE", 8, "1", "NA", 3),
        ("DL1ABC", 28, "18", "EU", 3),
        # another continent is five
        ("K6GTE", 8, "28", "EU", 5),
        ("DL1ABC", 28, "8", "NA", 5),
    ],
)
def test_points(my_call, zone, zn, continent, expected):
    assert load_contest(
        "iaru_hf", _ctx(zone, zn, continent, my_call=my_call)
    ).points() == (expected)


def test_continent_falls_back_to_the_country_file():
    # No CONTINENT in the contact: N0AX is North American, so from K6GTE (also
    # North America) a different zone is three points.
    assert load_contest("iaru_hf", _ctx(8, "1", None, his_call="N0AX")).points() == 3
    assert load_contest("iaru_hf", _ctx(8, "28", None, his_call="DL1ABC")).points() == 5


def test_a_duplicate_scores_nothing():
    ctx = _ctx(8, "8", "NA")
    ctx.contact_is_dupe = 1
    assert load_contest("iaru_hf", ctx).points() == 0


def test_class_metadata():
    assert Contest.DisplayName == "IARU HF"
    assert Contest.CabrilloName == "IARU-HF"
    assert Contest.Mode == "BOTH"
    assert Contest.ZoneType == "IARU"  # the exchange is the ITU zone
    assert Contest.DupeType == 3
    # the sent exchange is the fixed setting, so other_1 stays hidden
    assert Contest.EntryFields == ("field1", "field2", "field4")
    assert Contest.FrameText == ("SNT", "", "ITU Zone")
    assert "Mode" in Contest.LogInfo
    assert "RcvNr" in Contest.LogInfo


@pytest.mark.parametrize(
    "contact,zone,hq",
    [
        ({"ZN": 8}, "8", None),  # a zone number from the log
        ({"ZN": "8"}, "8", None),  # ... or typed
        ({"ZN": 0}, "0", None),
        ({"ZN": "ARRL"}, None, "ARRL"),  # an HQ station's society
        ({"ZN": ""}, None, None),  # nothing typed yet is no multiplier
        ({}, None, None),
    ],
)
def test_multiplier_keys_split_the_exchange(contact, zone, hq):
    contest = load_contest("iaru_hf", SimpleNamespace())
    assert contest.mult_value(1, contact) == zone
    assert contest.mult_value(2, contact) == hq


def test_sql_keys_split_the_zone_column():
    contest = load_contest("iaru_hf", SimpleNamespace())
    assert contest.mult_sql(1) == "CASE WHEN typeof(ZN) = 'integer' THEN ZN END"
    assert "typeof(ZN) != 'integer'" in contest.mult_sql(2)
    # both are counted once per band, not once per mode (rule 5.2.1)
    assert contest._mult_columns(1) == ("Band",)
    assert contest._mult_columns(2) == ("Band",)


def test_set_contact_vars_captures_the_zone():
    def field(text):
        return SimpleNamespace(text=lambda: text)

    ctx = SimpleNamespace(
        contact={"Call": "K6GTE", "CountryPrefix": "K"},
        sent=field("599"),
        receive=field("599"),
        other_1=field("8"),
        other_2=field("28"),
        contest_settings={"SentExchange": "8"},
    )
    load_contest("iaru_hf", ctx).set_contact_vars()
    assert ctx.contact["SNT"] == "599"
    assert ctx.contact["RCV"] == "599"
    assert ctx.contact["ZN"] == "28"
    assert ctx.contact["NR"] == "28"
    assert ctx.contact["SentNr"] == "8"


def test_prefill_fills_the_zone_from_the_contact():
    class Field:
        def __init__(self, text=""):
            self._text = text

        def text(self):
            return self._text

        def setText(self, text):
            self._text = text

    ctx = SimpleNamespace(
        contact={"ZN": "28"},
        other_1=Field(),
        other_2=Field(),
        contest_settings={"SentExchange": "8"},
    )
    load_contest("iaru_hf", ctx).prefill()
    assert ctx.other_2.text() == "28"
    assert ctx.other_1.text() == "8"


# -- the numbers the corpus cases produce --------------------------------------
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
    case = CASES[case_id]
    home = headless / f"{case.contest}-{case.name}"
    home.mkdir(parents=True, exist_ok=True)
    harness = ContestHarness(case.contest, case, home, monkeypatch)
    plugin_common.import_adif(harness)
    harness.score_log()
    return harness


@pytest.mark.parametrize("case_id", ["iaru_hf/K6GTE", "iaru_hf/DL1ABC"])
def test_show_mults_counts_zones_and_hq_once_per_band(case_id, headless, monkeypatch):
    """Zones 8, 28 and 18 on 14m plus ARRL are four multipliers, whatever the mode."""
    contest = loaded(case_id, headless, monkeypatch).contest
    assert contest.show_mults() == 4
    assert contest.get_mults() == {"state": 1, "zone": 3}


@pytest.mark.parametrize(
    "case_id,score",
    [("iaru_hf/K6GTE", 60), ("iaru_hf/DL1ABC", 52)],
)
def test_calc_score(case_id, score, headless, monkeypatch):
    assert loaded(case_id, headless, monkeypatch).contest.calc_score() == score
