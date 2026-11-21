"""Contest points rules: parsing and scoring."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from not1mm.lib.parse_udc import contest_from_udc, parse_udc_text, validate_udc
from not1mm.lib.points_rules import PointsRulesError, parse_points, score

LOOKUP = {
    "K1ABC": {"primary_pfx": "K", "continent": "NA", "cq": 5, "itu": 8},
    "DL1ABC": {"primary_pfx": "DL", "continent": "EU", "cq": 14, "itu": 28},
    "K6GTE": {"primary_pfx": "K", "continent": "NA", "cq": 3, "itu": 6},
}


def lookup(call):
    item = LOOKUP.get(call)
    return {call: item} if item else None


def contact(**overrides):
    base = {
        "Call": "K1ABC",
        "Band": 3.5,
        "Mode": "CW",
        "Exchange1": "",
        "MiscText": "",
        "Sect": "",
        "Comment": "",
        "GridSquare": "FN31",
        "CountryPrefix": "",
        "Continent": "",
        "CQZone": 0,
        "ITUZone": 0,
    }
    base.update(overrides)
    return base


def station(**overrides):
    base = {
        "Call": "K6GTE",
        "GridSquare": "DM13",
        "CountryPrefix": "",
        "Continent": "",
        "CQZone": 0,
        "ITUZone": 0,
    }
    base.update(overrides)
    return base


def worth(text, sent_exchange="", **overrides):
    return score(
        parse_points(text),
        contact=contact(**overrides),
        station=station(),
        lookup=lookup,
        sent_exchange=sent_exchange,
    )


# -- parsing ---------------------------------------------------------------


def test_a_plain_number_is_the_default():
    assert parse_points("2").default == 2
    assert not parse_points("2").is_rules


def test_an_empty_value_is_zero_for_the_parser():
    assert parse_points("").default == 0


def test_a_rule_list_is_parsed_in_pairs():
    points = parse_points("40m, 1, 80m, 2")
    assert [rule.kind for rule in points.rules] == ["band", "band"]
    assert [rule.points for rule in points.rules] == [1, 2]
    assert points.is_rules


def test_missing_commas_are_tolerated():
    # Real files write "20m 1" and "DIGI 3".
    points = parse_points("20m 1, 40m 3")
    assert [(r.kind, r.points) for r in points.rules] == [("band", 1), ("band", 3)]


def test_a_bare_number_where_a_rule_belongs_is_the_default():
    points = parse_points("1, ZS, 5")
    assert points.default == 1
    assert points.rules[0].kind == "country"


def test_an_odd_rule_list_is_an_error():
    with pytest.raises(PointsRulesError):
        parse_points("40m, 1, 80m")


def test_a_star_needs_a_field_rule():
    with pytest.raises(PointsRulesError):
        parse_points("40m, *")


def test_a_distance_table_is_parsed():
    points = parse_points("1/600/10; 601/1200/13")
    assert points.distance == ((1.0, 600.0, 10), (601.0, 1200.0, 13))


# -- the criteria ----------------------------------------------------------


def test_band_beats_mode_continent_and_country():
    text = "160m, 5, CW, 6, K, 7, OtherContinent, 8"
    assert worth(text, Band=1.8, Mode="CW", CountryPrefix="K") == 5


def test_mode_beats_continent_and_country():
    text = "CW, 3, K, 10, OtherContinent, 20"
    assert worth(text, Mode="CW", CountryPrefix="K", Continent="NA") == 3


def test_country_beats_continent():
    text = "K, 10, SameContinent, 20"
    assert worth(text, CountryPrefix="K", Continent="NA") == 10


def test_my_country_beats_same_continent():
    assert worth("MyCountry, 1, SameContinent, 2", CountryPrefix="K") == 1


def test_my_country_and_the_continents():
    text = "MyCountry, 1, SameContinent, 2, OtherContinent, 3"
    assert worth(text, CountryPrefix="K", Continent="NA") == 1
    assert worth(text, Call="K1ABC", CountryPrefix="K", Continent="NA") == 1
    # DL is Europe, the station is North America
    assert worth(text, Call="DL1ABC", CountryPrefix="DL", Continent="EU") == 3


def test_ssb_matches_usb_and_lsb():
    assert worth("SSB, 2", Mode="USB") == 2
    assert worth("SSB, 2", Mode="LSB") == 2
    assert worth("SSB, 2", Mode="CW") == 0


def test_digi_matches_ft8_and_rtty_has_its_own():
    assert worth("DIGI, 1, RTTY, 4", Mode="FT8") == 1
    assert worth("DIGI, 1, RTTY, 4", Mode="RTTY") == 4


def test_a_band_token_is_case_insensitive():
    assert worth("160M, 5", Band=1.8) == 5


def test_no_match_uses_the_default():
    assert worth("1, ZS, 5", CountryPrefix="K") == 1
    assert worth("ZS, 5", CountryPrefix="K") == 0


# -- explicit rules --------------------------------------------------------


def test_an_explicit_rule_beats_the_criteria():
    # The help says a SectIs_ rule must come first; any explicit rule wins
    # over the band/mode/continent/country tiers here.
    assert worth("CW, 1, ExchIs_YL, 2", Mode="CW", Exchange1="YL") == 2


def test_exch_is_matches_the_whole_exchange():
    assert worth("ExchIs_YL, 2, ExchIs_OM, 0", Exchange1="YL") == 2
    assert worth("ExchIs_YL, 2, ExchIs_OM, 0", Exchange1="OM") == 0


def test_exch_is_without_underscore_matches_inside():
    assert worth("ExchIsOB, 15", Exchange1="OB01") == 15


def test_sect_is_and_misc_is():
    assert worth("SectIs_TB, 7", Sect="TB") == 7
    assert worth("MiscIs_0, 1", MiscText="0") == 1


def test_is_misc_and_is_comment():
    assert worth("IsMisc, 3, IsComment, 1", MiscText="x") == 3
    assert worth("IsMisc, 3, IsComment, 1", Comment="x") == 1


def test_a_numeric_exchange():
    assert worth("ExchIsNum, 2, ExchIsNotNum, 1", Exchange1="12") == 2
    assert worth("ExchIsNum, 2, ExchIsNotNum, 1", Exchange1="YL") == 1


def test_an_empty_exchange():
    assert worth("ExchIs_Empty, 4", Exchange1="") == 4
    assert worth("ExchIs_Empty, 4", Exchange1="YL") == 0


def test_exchange_star_takes_the_number_from_the_field():
    assert worth("Exchange, *", Exchange1="15") == 15
    assert worth("Misc, *", MiscText="7") == 7


def test_a_suffix():
    assert worth("/P, 5", Call="K1ABC/P") == 5
    assert worth("/QRP, 3", Call="K1ABC/QRP") == 3
    assert worth("/P, 5", Call="K1ABC") == 0


def test_my_grid_and_zones():
    assert worth("MyGrid, 50", GridSquare="DM13AA") == 50
    assert worth("MyGrid, 50", GridSquare="FN31") == 0
    assert worth("MyCQZone, 2", CQZone=3) == 2
    assert worth("MyIARUZone, 2", ITUZone=6) == 2


def test_my_exchange():
    assert worth("MyExchange, 3", Exchange1="12", SentNr="12") == 3
    assert worth("MyExchange, 3", Exchange1="12", sent_exchange="12") == 3
    assert worth("MyExchange, 3", Exchange1="12", sent_exchange="13") == 0


def test_a_continent_and_band_combination():
    assert worth("SameContinent+80, 5", Band=3.5, CountryPrefix="K") == 5
    assert worth("OtherContinent+80, 6", Band=3.5, Call="DL1ABC") == 6
    assert worth("SameContinent+40, 5", Band=3.5, CountryPrefix="K") == 0


# -- additive values and distance ------------------------------------------


def test_a_plus_adds_to_the_base():
    assert worth("CW, 2, IsMisc, +3", Mode="CW", MiscText="x") == 5
    assert worth("IsMisc, +3", MiscText="x") == 3


def test_a_distance_table_scores_by_km():
    # DM13 to FN31 is some thousands of km; a table that covers everything.
    assert worth("1/30000/10", GridSquare="FN31") == 10
    assert worth("1/1/10", GridSquare="FN31") == 0


def test_a_distance_table_needs_both_grids():
    assert worth("1/30000/10", GridSquare="") == 0


# -- the contest factory ---------------------------------------------------

MINIMAL = """[Contest]
Name = TEST
DisplayName = Test Contest
CabrilloName = TEST
Mode = CW
DupeType = 2
EntryWindowInfo = SNTText, 450, RCVText, 450, Exchange1Text, 700
FrameText = SNT RCV Exch
"""


def factory(text):
    return contest_from_udc(parse_udc_text(text, "test"))


def test_a_rule_list_replaces_the_plain_points(monkeypatch):
    contest_class = factory(MINIMAL + "PointsPerContact = 40m, 1, 80m, 2\n")
    assert contest_class.PointsPerContact == 0
    assert contest_class.PointsRules == "40m, 1, 80m, 2"
    assert "PointsPerContact" not in contest_class.UdcUnimplemented

    contest = contest_class(SimpleNamespace())
    contest.parent = SimpleNamespace(
        contact=contact(Band=3.5),
        station=station(),
        contact_is_dupe=0,
        cty_lookup=lookup,
        contest_settings={"SentExchange": ""},
    )
    assert contest.points() == 2

    contest.parent.contact_is_dupe = 1
    assert contest.points() == 0


def test_a_plain_number_keeps_the_simple_path():
    contest_class = factory(MINIMAL + "PointsPerContact = 5\n")
    assert contest_class.PointsPerContact == 5
    assert contest_class.PointsRules == ""


def test_a_vhf_number_is_flagged():
    text = MINIMAL.replace("Name = TEST", "Name = VHFTEST") + "PointsPerContact = 1\n"
    udc = parse_udc_text(text, "vhf")
    assert "VHF contest scores by distance" in "\n".join(
        str(issue) for issue in validate_udc(udc)
    )
    assert "PointsPerContact:vhf" in factory(text).UdcUnimplemented


def test_an_unparseable_rule_list_is_an_error():
    udc = parse_udc_text(MINIMAL + "PointsPerContact = 40m, 1, 80m\n", "broken")
    errors = [issue for issue in validate_udc(udc) if issue.level == "error"]
    assert [issue.key for issue in errors] == ["PointsPerContact"]
