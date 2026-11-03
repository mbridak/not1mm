"""The RDA Contest points table and its DXCC country grouping.

Reference:
  http://rdaward.org/rdac1.htm  (rules 9, 10)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins.rda_contest import country_mult_prefix, points

# call -> (entity, continent), the fields the country file gives.
_ENTITIES = {
    "K6GTE": ("United States", "NA"),
    "UA3ABC": ("European Russia", "EU"),
    "UA9ABC": ("Asiatic Russia", "AS"),
    "UA2ABC": ("Kaliningrad", "EU"),
    "DL1ABC": ("Fed. Rep. of Germany", "EU"),
    "N0AX": ("United States", "NA"),
}


def _ctx(my_call, his_call, dupe=0):
    def cty(call):
        entity, continent = _ENTITIES[call]
        return {"0": {"entity": entity, "continent": continent}}

    return SimpleNamespace(
        contact_is_dupe=dupe,
        contact={"Call": his_call},
        station={"Call": my_call},
        cty_lookup=cty,
    )


@pytest.mark.parametrize(
    "my_call,his_call,expected",
    [
        # a Russian station: 1 against a Russian on its continent, 2 against
        # one on another, 3 for another country on its own continent and 5 for
        # another continent.
        ("UA3ABC", "UA3ABC", 1),
        ("UA3ABC", "UA2ABC", 1),  # Kaliningrad scores as European Russia
        ("UA3ABC", "UA9ABC", 2),
        ("UA3ABC", "DL1ABC", 3),
        ("UA3ABC", "N0AX", 5),
        # a non-Russian station: 10 for a Russian, nothing for anyone else.
        ("K6GTE", "UA3ABC", 10),
        ("K6GTE", "UA9ABC", 10),
        ("K6GTE", "UA2ABC", 10),
        ("K6GTE", "DL1ABC", 0),
        ("K6GTE", "N0AX", 0),
    ],
)
def test_points(my_call, his_call, expected):
    assert points(_ctx(my_call, his_call)) == expected


def test_a_duplicate_scores_nothing():
    assert points(_ctx("K6GTE", "UA3ABC", dupe=1)) == 0


@pytest.mark.parametrize(
    "prefix,expected",
    [
        ("UA", "UA"),
        ("UA9", "UA9"),
        ("UA2", "UA2"),
        ("dl", "DL"),
    ],
)
def test_country_multiplier_is_one_per_dxcc_entity(prefix, expected):
    # European Russia and Asiatic Russia are separate DXCC entities, and
    # Kaliningrad is a third.
    assert country_mult_prefix(prefix) == expected
