"""Point values for the ARRL 10-Meter Contest.

The corpus only carries CW and SSB contacts, so it cannot tell the old
substring-based mode test apart from the fixed one.  Pin the per-mode values
directly.

Reference:
  https://contests.arrl.org/ContestRules/10M-Rules.pdf  (rule 5.1)
"""

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest


def _contest(mode="CW", is_dupe=0):
    """The contest bound to a stand-in main window."""
    parent = SimpleNamespace(contact_is_dupe=is_dupe, contact={"Mode": mode})
    return load_contest("arrl_10m", parent)


@pytest.mark.parametrize("mode", ["SSB", "USB", "LSB", "FM", "AM", "PH", "ssb"])
def test_phone_is_two_points(mode):
    assert _contest(mode).points() == 2


@pytest.mark.parametrize("mode", ["CW", "CW-U", "CW-L", "CWR", "CW-R", "cw"])
def test_cw_is_four_points(mode):
    assert _contest(mode).points() == 4


@pytest.mark.parametrize("mode", ["RTTY", "DG", "FT8", "PSK31", "", "S", "P"])
def test_other_modes_score_nothing(mode):
    assert _contest(mode).points() == 0


def test_dupe_scores_nothing():
    assert _contest("CW", is_dupe=1).points() == 0
