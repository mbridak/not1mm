"""JIDX: the JA-DX point table, the prefecture multiplier and the category.

Rule 5 gives points only to a contact with exactly one Japanese end, and rule 6
makes each prefecture a multiplier per band -- but only on a contact that
scored, which is what keeps the CQ zone a DX station sends out of the count.
The corpus runs both sides; pin the pieces here so they cannot go back.

Reference:
  https://www.jidx.org/jidxrule-e.html  (rules 5, 6)
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from contest_harness import ContestHarness, DummyProgress, cty_lookup, discover_cases

from not1mm.lib import plugin_common
from not1mm.lib.contest import load_contest

PLUGINS = ["jidx_cw", "jidx_ph"]


def _ctx(mycall, hiscall, freq=14040, band=14.0, is_dupe=0):
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall, "Freq": freq, "Band": band},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "freq,mhz,expected",
    [
        (1830, 1, 4),  # 160m
        (3530, 3, 2),  # 80m
        (7030, 7, 1),  # 40m
        (14040, 14, 1),  # 20m
        (21040, 21, 1),  # 15m
        (28040, 28, 2),  # 10m
        (10120, 10, 0),  # 30m is not a JIDX band
    ],
)
def test_points_by_band(plugin, freq, mhz, expected):
    assert (
        load_contest(plugin, _ctx("K6GTE", "JA1ABC", freq=freq, band=mhz)).points()
        == expected
    )


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        ("K6GTE", "JA1ABC", 1),  # a DX entrant scores the JA stations
        ("JA1ABC", "K6GTE", 1),  # and a JA entrant the DX stations
        ("K6GTE", "DL1ABC", 0),  # DX-DX scores nothing
        ("JA1ABC", "JA2DEF", 0),  # nor does JA-JA
    ],
)
def test_only_a_ja_dx_contact_scores(plugin, mycall, hiscall, expected):
    assert load_contest(plugin, _ctx(mycall, hiscall)).points() == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_duplicate_scores_nothing(plugin):
    assert load_contest(plugin, _ctx("K6GTE", "JA1ABC", is_dupe=1)).points() == 0


@pytest.mark.parametrize("plugin", PLUGINS)
def test_class_metadata(plugin):
    contest = load_contest(plugin, SimpleNamespace())
    assert contest.CabrilloName == ("JIDX-CW" if plugin == "jidx_cw" else "JIDX-SSB")
    assert contest.Mode == ("CW" if plugin == "jidx_cw" else "SSB")
    assert contest.DupeType == 2
    assert contest.NumMults == 1
    assert contest.IsMult1Per == 1
    assert contest._mult_columns(1) == ("Band",)
    assert contest.mult_sql(1) == "CASE WHEN Points > 0 THEN NR END"


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "contact,expected",
    [
        ({"NR": 1}, 1),  # a logged row: the column hands back an int
        ({"NR": "1"}, 1),  # the entry field: text, compared as the column stores it
        ({"NR": " 13 "}, 13),
        ({"NR": ""}, None),
        ({"NR": None}, None),
        ({"NR": "AB"}, None),  # not a prefecture number
        ({}, None),
    ],
)
def test_the_received_number_is_the_key(plugin, contact, expected):
    assert load_contest(plugin, SimpleNamespace()).mult_value(1, contact) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_contact_that_scores_carries_the_multiplier(plugin):
    class Field:
        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

    class Database:
        def mult_key_exists(self, expression, value, per=(), band=None, mode=None):
            assert per == ("Band",)
            assert band == 14.0
            return {"count": 0}

    app = SimpleNamespace(
        contact={"Call": "JA1ABC", "Freq": 14040, "Band": 14.0},
        contact_is_dupe=0,
        station={"Call": "K6GTE"},
        sent=Field("599"),
        receive=Field("599"),
        other_1=Field("3"),
        other_2=Field("1"),
        cty_lookup=cty_lookup,
        database=Database(),
    )
    load_contest(plugin, app).set_contact_vars()
    assert app.contact["NR"] == "1"
    assert app.contact["SentNr"] == "3"
    assert app.contact["IsMultiplier1"] == 1


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_dx_dx_contact_carries_no_multiplier(plugin):
    class Field:
        def __init__(self, text):
            self._text = text

        def text(self):
            return self._text

    app = SimpleNamespace(
        contact={"Call": "DL1ABC", "Freq": 14040, "Band": 14.0},
        contact_is_dupe=0,
        station={"Call": "K6GTE"},
        sent=Field("599"),
        receive=Field("599"),
        other_1=Field("3"),
        other_2=Field("14"),
        cty_lookup=cty_lookup,
    )
    load_contest(plugin, app).set_contact_vars()
    assert app.contact["IsMultiplier1"] == 0


@pytest.mark.parametrize(
    "band,power,single_op,transmitters,expected",
    [
        ("ALL", "HIGH", True, "ONE", "AB"),
        ("ALL", "LOW", True, "ONE", "ABL"),
        ("ALL", "QRP", True, "ONE", "ABL"),
        ("40M", "LOW", True, "ONE", "7L"),
        ("20M", "HIGH", True, "ONE", "14"),
        ("160M", "HIGH", True, "ONE", "1.8"),
        ("ALL", "HIGH", False, "ONE", "MOP1"),
        ("ALL", "HIGH", False, "TWO", "MOP2"),
    ],
)
def test_the_cabrillo_category(band, power, single_op, transmitters, expected):
    app = SimpleNamespace(
        contest_settings={
            "OperatorCategory": "SINGLE-OP" if single_op else "MULTI-OP",
            "BandCategory": band,
            "PowerCategory": power,
            "TransmitterCategory": transmitters,
        }
    )
    assert load_contest("jidx_cw", app)._category() == expected


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


@pytest.mark.parametrize(
    "case_id,mults,score",
    [
        ("jidx_cw/K6GTE", 5, 50),
        ("jidx_cw/K6GTE-40M", 2, 4),
        ("jidx_ph/K6GTE", 5, 50),
        ("jidx_ph/K6GTE-40M", 2, 4),
    ],
)
def test_the_corpus_counts(case_id, mults, score, headless, monkeypatch):
    contest = loaded(case_id, headless, monkeypatch).contest
    assert contest.show_mults() == mults
    assert contest.get_mults() == {"country": mults}
    assert contest.calc_score() == score
