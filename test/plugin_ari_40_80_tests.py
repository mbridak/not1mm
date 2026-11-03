"""Point values for the ARI 40/80 Contest.

The mode table used to be a substring test, so `""` scored as phone and a CW
variant like "CW-U" scored nothing.  Pin the values directly.

References:
  http://www.ari.it/en/contest-hf/contest-4080.html
      (1 point phone, 2 digital, 3 CW)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import ari_40_80


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
    context = SimpleNamespace(contact_is_dupe=0, contact={"Mode": mode})
    assert ari_40_80.points(context) == expected


def test_dupe_scores_nothing():
    context = SimpleNamespace(contact_is_dupe=1, contact={"Mode": "CW"})
    assert ari_40_80.points(context) == 0


def test_cabrillo_name():
    assert ari_40_80.cabrillo_name == "40-80"
