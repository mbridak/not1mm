"""DARC VHF: one point per kilometre, and the band/mode duplicate grouping.

Reference:
  https://www.darc.de/der-club/referate/conteste/ukw/tnukwcontest001/tnukwcontest007000/
"""

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest
from not1mm.plugins.darc_vhf import _dupe_mode


def _contest(grid, my_grid="JN58", dupe=0):
    parent = SimpleNamespace(
        contact_is_dupe=dupe,
        contact={"Exchange1": grid},
        station={"GridSquare": my_grid},
    )
    return load_contest("darc_vhf", parent)


def test_points_are_one_per_kilometre():
    # JN58 to JO31 is 441 km and to JN49 is 185 km.
    assert _contest("JO31").points() == 441
    assert _contest("JN49").points() == 185


def test_the_same_grid_scores_the_minimum():
    assert _contest("JN58").points() == 1


def test_a_duplicate_scores_nothing():
    assert _contest("JO31", dupe=1).points() == 0


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
    assert _dupe_mode(mode) == group
