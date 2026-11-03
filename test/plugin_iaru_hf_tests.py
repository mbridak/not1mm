"""IARU HF World Championship points.

Reference:
  https://contests.arrl.org/ContestRules/IARU-HF-Rules.pdf  (rules 5.1, 5.2)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins.iaru_hf import points

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
    assert points(_ctx(zone, zn, continent, my_call=my_call)) == expected


def test_continent_falls_back_to_the_country_file():
    # No CONTINENT in the contact: N0AX is North American, so from K6GTE (also
    # North America) a different zone is three points.
    assert points(_ctx(8, "1", None, his_call="N0AX")) == 3
    assert points(_ctx(8, "28", None, his_call="DL1ABC")) == 5


def test_a_duplicate_scores_nothing():
    ctx = _ctx(8, "8", "NA")
    ctx.contact_is_dupe = 1
    assert points(ctx) == 0
