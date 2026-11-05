"""Point values for the ES Open HF Championship.

The corpus runs an Estonian and a foreign entrant, but not every branch - an
empty mode, or a mode letter the old substring test matched by accident.

References:
  https://erau.ee/images/LL/ES-Open_rules.pdf  (QSO Points, Multiplier)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.plugins import es_open


def _ctx(mycall, hiscall, mode="CW", is_dupe=0):
    """Minimal fake `self` for es_open.points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall, "Mode": mode},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("CW", 2),
        ("CW-U", 2),
        ("CWR", 2),
        ("SSB", 1),
        ("USB", 1),
        ("LSB", 1),
        ("FM", 1),
        ("AM", 1),
        ("PH", 1),
        # The old test was a substring match: an empty mode scored phone, and
        # so did any single letter the list contains.
        ("", 0),
        ("RTTY", 0),
        ("PSK31", 0),
        ("S", 0),
        ("B", 0),
    ],
)
def test_points_by_mode(mode, expected):
    assert es_open.points(_ctx("ES1ABC", "ES2DEF", mode)) == expected


def test_foreign_entrant_only_scores_estonians():
    assert es_open.points(_ctx("K6GTE", "ES2DEF")) == 2
    assert es_open.points(_ctx("K6GTE", "DL1ABC")) == 0


def test_estonian_entrant_scores_everyone():
    assert es_open.points(_ctx("ES1ABC", "DL1ABC")) == 2
    assert es_open.points(_ctx("ES1ABC", "K6GTE")) == 2


def test_dupe_scores_nothing():
    assert es_open.points(_ctx("ES1ABC", "ES2DEF", is_dupe=1)) == 0
