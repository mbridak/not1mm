"""VHF & Up Sprints: one point a QSO on the low bands, distance on microwave.

Reference:
  https://sites.google.com/site/springvhfupsprints/home/2026-information
  (rule 6.1, rule 6.3)
"""

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest


def _ctx(band, nr="FN31", my_grid="DM13", dupe=0):
    return SimpleNamespace(
        contact_is_dupe=dupe,
        contact={"Band": band, "NR": nr},
        station={"GridSquare": my_grid},
    )


@pytest.mark.parametrize(
    "band,expected",
    [
        (50.0, 1),
        (144.0, 1),
        (222.0, 1),
        (432.0, 1),
        # a band outside the sprint's set scores nothing
        (1.8, 0),
        (28.0, 0),
    ],
)
def test_low_bands_score_one_point(band, expected):
    assert load_contest("vhf_sprint", _ctx(band)).points() == expected


@pytest.mark.parametrize("band", [902.0, 1296.0, 2300.0, 10368.0])
def test_microwave_scores_the_distance(band):
    # DM13 to FN31 is 3965 km - the Microwave Sprint is distance based, not
    # one point.
    assert load_contest("vhf_sprint", _ctx(band)).points() == 3965


def test_microwave_has_a_minimum_of_one():
    assert load_contest("vhf_sprint", _ctx(1296.0, nr="DM13")).points() == 1


def test_a_duplicate_scores_nothing():
    assert load_contest("vhf_sprint", _ctx(144.0, dupe=1)).points() == 0
