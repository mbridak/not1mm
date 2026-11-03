"""Point values for the Dutch PACC contest.

Which side the entrant is on - and whether the other station is Dutch - is
what decides a point, and the two used to be read from the entry field, so an
imported foreign log scored nothing.  The corpus runs both sides; pin the
values here so it cannot come back.

Reference:
  https://veron.nl/vereniging/commissies-en-werkgroepen/traffic-bureau/
  hf-contesten/pacc-rules/  (rule 7.1)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.plugins import pacc


def _ctx(mycall, hiscall, is_dupe=0):
    """Minimal fake `self` for pacc.points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        # A Dutch entrant scores for every contact.
        ("PA1ABC", "DL1ABC", 1),
        ("PA1ABC", "K6GTE", 1),
        ("PA1ABC", "PA2DEF", 1),
        # A foreign entrant only for Dutch stations.
        ("K6GTE", "PA1ABC", 1),
        ("K6GTE", "DL1ABC", 0),
        ("K6GTE", "W1AW", 0),
    ],
)
def test_points(mycall, hiscall, expected):
    assert pacc.points(_ctx(mycall, hiscall)) == expected


def test_dupe_scores_nothing():
    assert pacc.points(_ctx("K6GTE", "PA1ABC", is_dupe=1)) == 0
