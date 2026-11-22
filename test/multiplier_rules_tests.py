"""UDC's multiplier rules: per-slot filters, MultMult and the band set."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import (
    MULT_KEYS,
    MULTIPLIER_BANDS,
    calculate_wpx_prefix,
)
from not1mm.lib.parse_udc import contest_from_udc, parse_udc_text, validate_udc

LOOKUP = {
    "K6GTE": {"primary_pfx": "K", "continent": "NA", "cq": 3, "itu": 6},
    "DL1ABC": {"primary_pfx": "DL", "continent": "EU", "cq": 14, "itu": 28},
}

BASE = """[Contest]
Name = TEST
DisplayName = Test Contest
CabrilloName = TEST
Mode = CW
DupeType = 2
EntryWindowInfo = SNTText, 450, RCVText, 450, Exchange1Text, 700
FrameText = SNT RCV Exch
NumMults = 1
Multiplier1Name = Sect
MultSqlString = Section
IsMult1Per = 1
"""


class Database:
    def fetch_points(self):
        return {"Points": 10}


class Parent:
    station = {"Call": "K6GTE", "ARRLSection": "ORG"}
    contact = {}
    contact_is_dupe = 0
    contest_settings = {"SentExchange": ""}
    database = Database()

    def cty_lookup(self, call):
        item = LOOKUP.get(call)
        return {call: item} if item else None


def build(extra=""):
    return contest_from_udc(parse_udc_text(BASE + extra, "test"))


def contest(extra=""):
    return build(extra)(Parent())


def contact(**overrides):
    base = {
        "Call": "DL1ABC",
        "Band": 3.5,
        "Mode": "CW",
        "Sect": "ORG",
        "CountryPrefix": "DL",
        "Continent": "EU",
        "Exchange1": "001",
    }
    base.update(overrides)
    return base


def test_members_of_the_multiplier_vocabulary():
    assert "Comment" in MULT_KEYS
    assert MULT_KEYS["Comment"][1]({"Comment": "x"}) == "x"


def test_count_mult_only_for_countries():
    rule = contest("CountMultOnlyFor = DL, G\n")
    assert rule.mult_value(1, contact(CountryPrefix="DL")) == "ORG"
    assert rule.mult_value(1, contact(CountryPrefix="G")) == "ORG"
    assert rule.mult_value(1, contact(CountryPrefix="K", Continent="NA")) is None


def test_count_mult_only_for_a_continent():
    rule = contest("CountMultOnlyFor = NA\n")
    assert rule.mult_value(1, contact(Continent="NA", CountryPrefix="K")) == "ORG"
    assert rule.mult_value(1, contact(Continent="EU")) is None


def test_do_not_count_mult_only_for():
    rule = contest("DoNotCountMultOnlyFor = NA\n")
    assert rule.mult_value(1, contact(Continent="NA", CountryPrefix="K")) is None
    assert rule.mult_value(1, contact(Continent="EU")) == "ORG"


def test_count_mult_only_for_sections():
    rule = contest("CountMultOnlyForSec = ORG, EB\n")
    assert rule.mult_value(1, contact(Sect="ORG")) == "ORG"
    assert rule.mult_value(1, contact(Sect="EB")) == "EB"
    assert rule.mult_value(1, contact(Sect="ZZ")) is None


def test_do_not_count_my_country():
    text = BASE.replace("MultSqlString = Section", "MultSqlString = CountryPrefix")
    rule = contest_from_udc(
        parse_udc_text(text + "DoNotCountMeAsMult = True\n", "test")
    )(Parent())
    assert rule.mult_value(1, contact(CountryPrefix="K")) is None
    assert rule.mult_value(1, contact(CountryPrefix="DL")) == "DL"


def test_do_not_count_my_section():
    rule = build("DoNotCountMeAsMult = True\n")(Parent())
    assert rule.mult_value(1, contact(Sect="ORG")) is None
    assert rule.mult_value(1, contact(Sect="EB")) == "EB"


def test_do_not_count_my_wpx():
    text = BASE.replace("MultSqlString = Section", "MultSqlString = WPXPrefix")
    rule = contest_from_udc(
        parse_udc_text(text + "DoNotCountMeAsMult = True\n", "test")
    )(Parent())
    mine = calculate_wpx_prefix("K6GTE")
    assert rule.mult_value(1, contact(WPXPrefix=mine)) is None
    assert rule.mult_value(1, contact(WPXPrefix="DL")) == "DL"


def test_multiplier_bands():
    hf = contest("MultiplierBands = 1\n")
    assert hf.mult_value(1, contact(Band=3.5)) == "ORG"
    assert hf.mult_value(1, contact(Band=50)) is None

    vhf = contest("MultiplierBands = 3\n")
    assert vhf.mult_value(1, contact(Band=50)) == "ORG"


def test_the_all_hf_set_uses_the_canonical_30m_value():
    # ham_utility's table has 30m at 10.0, not 10.1.
    assert 10.0 in MULTIPLIER_BANDS[2]
    assert 10.1 not in MULTIPLIER_BANDS[2]
    rule = contest("MultiplierBands = 2\n")
    assert rule.mult_value(1, contact(Band=10.0)) == "ORG"
    assert rule.mult_value(1, contact(Band=10.1)) is None


def test_the_sql_gets_the_same_filters():
    rule = contest(
        "CountMultOnlyFor = DL, NA\n"
        "DoNotCountMultOnlyFor = K\n"
        "CountMultOnlyForSec = ORG\n"
        "DoNotCountMeAsMult = True\n"
        "MultiplierBands = 1\n"
    )
    sql = rule.mult_sql(1)
    assert "Band IN" in sql
    assert "upper(CountryPrefix) IN" in sql
    assert "upper(Continent) IN" in sql
    assert "NOT (" in sql
    assert "upper(Sect) IN" in sql
    assert "upper(Sect) !=" in sql


def test_mult_mult_zero_is_shown_but_not_scored():
    text = BASE.replace("NumMults = 1", "NumMults = 2") + (
        "MultSqlString2 = CountryPrefix\nMultMult2 = 0\n"
    )
    rule = contest_from_udc(parse_udc_text(text, "test"))(Parent())
    rule._mult_count = lambda slot: {1: 5, 2: 7}[slot]
    assert rule._mult_scored(1)
    assert not rule._mult_scored(2)
    assert rule.show_mults() == 5
    assert rule.calc_score() == 50
    assert list(rule.get_mults()) == ["state"]


def test_a_legacy_num_mults_still_reaches_the_score():
    rule = build("")(Parent())
    rule._mult_count = lambda slot: 5
    assert rule.calc_score() == 50


def test_the_udc_attributes_are_parsed():
    rule = build(
        "MultMult2 = 0\n"
        "DoNotCountMeAsMult = True\n"
        "CountMultOnlyFor = dl, na\n"
        "CountMultOnlyForSec = org\n"
        "DoNotCountMultOnlyFor = k\n"
    )
    contest_class = rule
    assert contest_class.MultMult == 1
    assert contest_class.MultMult2 == 0
    assert contest_class.DoNotCountMeAsMult is True
    assert contest_class.CountMultOnlyFor == ("DL", "NA")
    assert contest_class.CountMultOnlyForSec == ("ORG",)
    assert contest_class.DoNotCountMultOnlyFor == ("K",)
    # N1MM's default band set is 1 when the file leaves it empty.
    assert contest_class.MultiplierBands == 1


@pytest.mark.parametrize(
    "text,key",
    [
        ("MultMult = 2\n", "MultMult"),
        ("DoNotCountMeAsMult = maybe\n", "DoNotCountMeAsMult"),
        ("MultiplierBands = 9\n", "MultiplierBands"),
    ],
)
def test_bad_multiplier_rule_values_are_errors(text, key):
    udc = parse_udc_text(BASE + text, "test")
    errors = [issue for issue in validate_udc(udc) if issue.level == "error"]
    assert [issue.key for issue in errors] == [key]
