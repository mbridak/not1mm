"""DARC VHF: one point per kilometre, and the band/mode duplicate grouping.

Reference:
  https://www.darc.de/der-club/referate/conteste/ukw/tnukwcontest001/tnukwcontest007000/
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import darc_vhf


def _ctx(grid, my_grid="JN58", dupe=0):
    return SimpleNamespace(
        contact_is_dupe=dupe,
        contact={"Exchange1": grid},
        station={"GridSquare": my_grid},
    )


def test_points_are_one_per_kilometre():
    # JN58 to JO31 is 441 km and to JN49 is 185 km.
    assert darc_vhf.points(_ctx("JO31")) == 441
    assert darc_vhf.points(_ctx("JN49")) == 185


def test_the_same_grid_scores_the_minimum():
    assert darc_vhf.points(_ctx("JN58")) == 1


def test_a_duplicate_scores_nothing():
    assert darc_vhf.points(_ctx("JO31", dupe=1)) == 0


@pytest.mark.parametrize(
    "mode,group",
    [
        ("SSB", "PH"),
        ("FM", "PH"),
        ("AM", "PH"),
        ("CW", "CW"),
        ("CW-U", "CW"),
        ("RTTY", "DI"),
        ("FT8", "DI"),
        ("FT4", "DI"),
        ("OTHERMODE", "OTHER"),
    ],
)
def test_dupe_mode_groups_like_the_band_mode_check(mode, group):
    assert darc_vhf._dupe_mode(mode) == group
