"""Point values for the Helvetia Contest.

An HB contact is 10 points to anyone, including another HB station; the rest
of the table is 1 point within a continent and 3 across one.

References:
  https://www.contestcalendar.com/contestdetails.php?ref=326  (QSO Points)
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
    return load_contest("helvetia", parent)


@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        ("K6GTE", "HB9ABC", 10),
        ("HB9ABC", "HB9XYZ", 10),
        ("K6GTE", "DL1ABC", 3),
        ("K6GTE", "W1AW", 1),
        ("HB9ABC", "DL1ABC", 1),
        ("HB9ABC", "W1AW", 3),
    ],
)
def test_points(mycall, hiscall, expected):
    assert _contest(mycall, hiscall).points() == expected


def test_dupe_scores_nothing():
    assert _contest("K6GTE", "HB9ABC", is_dupe=1).points() == 0
