"""Point values for the LZ DX Contest.

The rules give an LZ contact 10 points, but only 1 point between two LZ
stations; the corpus cannot separate those without an LZ entrant, so pin the
values directly.

References:
  https://lzdx.bfra.bg/rulesen.html  (QSO Points, Multipliers)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.lib.contest import load_contest


def _contest(mycall, hiscall, is_dupe=0):
    """The contest bound to a stand-in main window."""
    parent = SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall},
        cty_lookup=cty_lookup,
    )
    return load_contest("lz-dx", parent)


@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        # A foreign entrant: any LZ station is 10.
        ("K6GTE", "LZ1ABC", 10),
        ("K6GTE", "DL1ABC", 3),
        ("K6GTE", "W1AW", 1),
        # An LZ entrant: 1 to another LZ station, 1 within Europe, 3 outside.
        ("LZ1ABC", "LZ2XYZ", 1),
        ("LZ1ABC", "DL1ABC", 1),
        ("LZ1ABC", "W1AW", 3),
        ("LZ1ABC", "JA1ABC", 3),
    ],
)
def test_points(mycall, hiscall, expected):
    assert _contest(mycall, hiscall).points() == expected


def test_dupe_scores_nothing():
    assert _contest("K6GTE", "LZ1ABC", is_dupe=1).points() == 0


def test_unknown_station_scores_nothing():
    assert _contest("K6GTE", "QQ1QQQ").points() == 0
