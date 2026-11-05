"""The geographic points for the RAEM contest.

The corpus exercises them, but the hemisphere sign and the way round the globe
are decisions worth pinning on their own.

Reference:
  https://raem.srr.ru/rules/  (rule 5)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins.raem import latlondif


def _ctx(ours):
    """Minimal fake `self` for latlondif()."""
    return SimpleNamespace(contest_settings={"SentExchange": ours})


@pytest.mark.parametrize(
    "ours,theirs,expected",
    [
        # 117 west to 37 east is 154 degrees, not 80 - the hemispheres set the
        # sign.
        ("33N117W", "55N037O", 22 + 154),
        ("33N117W", "69N018O", 36 + 135),
        # 174 east to 117 west is 69 degrees the other way round the globe,
        # and a southern station is 69 away in latitude.
        ("33N117W", "36S174O", 69 + 69),
        ("33N117W", "33N117W", 0),
    ],
)
def test_coordinate_points(ours, theirs, expected):
    points, _polar = latlondif(_ctx(ours), theirs)
    assert points == expected


@pytest.mark.parametrize(
    "theirs,expected",
    [
        ("69N018O", True),
        ("66S010W", True),
        ("55N037O", False),
        ("36S174O", False),
    ],
)
def test_polar(theirs, expected):
    _points, polar = latlondif(_ctx("33N117W"), theirs)
    assert polar is expected


def test_an_unparsable_exchange_scores_no_coordinate_points():
    assert latlondif(_ctx("33N117W"), "") == (0, False)
    assert latlondif(_ctx("33N117W"), "55N037E") == (0, False)
