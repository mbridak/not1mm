"""TA VHF/UHF: the distance is scaled by band and mode.

Reference:
  https://trac.org.tr/tr/ta-vhf-uhf-contest-2025-english  (scoring)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins.ta_vhf_uhf_contest import points


def _ctx(band, mode, grid="KN50", my_grid="KN41"):
    return SimpleNamespace(
        contact_is_dupe=0,
        contact={"Band": band, "Exchange1": grid, "Mode": mode},
        station={"GridSquare": my_grid},
    )


# KN41 to KN50 is 202 km.
@pytest.mark.parametrize(
    "band,mode,expected",
    [
        # 6m x1
        (50.0, "FM", 202),
        (50.0, "SSB", 404),
        (50.0, "CW", 606),
        # 2m x2 - the band column holds the float 144.0, which the string
        # "144" never matched, so this factor used to be ignored
        (144.0, "FM", 404),
        (144.0, "SSB", 808),
        (144.0, "CW", 1212),
        # 70cm x3
        (432.0, "FM", 606),
        (432.0, "SSB", 1212),
        (432.0, "CW", 1818),
    ],
)
def test_band_and_mode_multipliers(band, mode, expected):
    assert points(_ctx(band, mode)) == expected


def test_a_duplicate_scores_nothing():
    ctx = _ctx(144.0, "CW")
    ctx.contact_is_dupe = 1
    assert points(ctx) == 0
