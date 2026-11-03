"""Point values for the ARRL 10-Meter Contest.

The corpus only carries CW and SSB contacts, so it cannot tell the old
substring-based mode test apart from the fixed one.  Pin the per-mode values
directly.

Reference:
  https://contests.arrl.org/ContestRules/10M-Rules.pdf  (rule 5.1)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import arrl_10m


def _ctx(mode="CW", is_dupe=0):
    """Minimal fake `self` for points()."""
    return SimpleNamespace(contact_is_dupe=is_dupe, contact={"Mode": mode})


@pytest.mark.parametrize("mode", ["SSB", "USB", "LSB", "FM", "AM", "PH", "ssb"])
def test_phone_is_two_points(mode):
    assert arrl_10m.points(_ctx(mode)) == 2


@pytest.mark.parametrize("mode", ["CW", "CW-U", "CW-L", "CWR", "CW-R", "cw"])
def test_cw_is_four_points(mode):
    assert arrl_10m.points(_ctx(mode)) == 4


@pytest.mark.parametrize("mode", ["RTTY", "DG", "FT8", "PSK31", "", "S", "P"])
def test_other_modes_score_nothing(mode):
    assert arrl_10m.points(_ctx(mode)) == 0


def test_dupe_scores_nothing():
    assert arrl_10m.points(_ctx("CW", is_dupe=1)) == 0
