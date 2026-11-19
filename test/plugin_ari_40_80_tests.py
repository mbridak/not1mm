"""Point values for the ARI 40/80 Contest.

The mode table used to be a substring test, so `""` scored as phone and a CW
variant like "CW-U" scored nothing.  Pin the values directly.

References:
  http://www.ari.it/en/contest-hf/contest-4080.html
      (1 point phone, 2 digital, 3 CW)
"""

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import contest_metadata, load_contest


def _contest(mode, is_dupe=0):
    """The contest bound to a stand-in main window."""
    parent = SimpleNamespace(contact_is_dupe=is_dupe, contact={"Mode": mode})
    return load_contest("ari_40_80", parent)


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("SSB", 1),
        ("USB", 1),
        ("LSB", 1),
        ("FM", 1),
        ("AM", 1),
        ("PH", 1),
        ("RTTY", 2),
        ("RY", 2),
        ("CW", 3),
        ("CW-U", 3),
        ("CW-L", 3),
        ("CWR", 3),
        ("", 0),
        ("PSK31", 0),
        ("FT8", 0),
    ],
)
def test_points(mode, expected):
    assert _contest(mode).points() == expected


def test_dupe_scores_nothing():
    assert _contest("CW", is_dupe=1).points() == 0


def test_cabrillo_name():
    assert contest_metadata("ari_40_80").CabrilloName == "40-80"
