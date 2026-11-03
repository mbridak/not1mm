"""Point values for the REF contest (Coupe du REF).

The corpus runs a French and a foreign entrant, but not every branch - a
French station working another French station on a different continent, for
one - and the two tables are easy to transpose.

References:
  https://concours.r-e-f.org/contest/a-propos  (QSO Points)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.plugins import ref_cw


def _ctx(mycall, hiscall, is_dupe=0):
    """Minimal fake `self` for ref_cw.points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        # A French entrant.
        ("F5ABC", "F6XYZ", 6),  # another French station, same continent
        ("F5ABC", "FG5ABC", 15),  # Guadeloupe is on another continent
        ("F5ABC", "DL1ABC", 1),
        ("F5ABC", "K6GTE", 2),
        # A foreign entrant: only French stations score.
        ("K6GTE", "F5ABC", 3),
        ("K6GTE", "FG5ABC", 1),  # Guadeloupe is in North America
        ("K6GTE", "DL1ABC", 0),
        ("K6GTE", "W1AW", 0),
        # A DOM/TOM entrant uses the French table too.
        ("FG5ABC", "F5ABC", 15),
        ("FG5ABC", "K6GTE", 1),
    ],
)
def test_points(mycall, hiscall, expected):
    assert ref_cw.points(_ctx(mycall, hiscall)) == expected


def test_dupe_scores_nothing():
    assert ref_cw.points(_ctx("F5ABC", "F6XYZ", is_dupe=1)) == 0
