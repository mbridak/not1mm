"""Point values for the ARI International DX Contest.

The corpus cannot reach every branch: no contact between two Italian stations
is permitted at all, so a valid Italian log never contains one, yet the plugin
must still score such a contact as nothing rather than as 10.  Pin the values
directly.

References:
  https://qrzonline.com/a-r-i-international-dx-contest-2025-may-3-4-2025
      (rule 2 Aim, rule 8 QSO/Points)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.plugins import ari_dx


def _ctx(mycall, hiscall, is_dupe=0):
    """Minimal fake `self` for ari_dx.points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        # No Italian-to-Italian contact is permitted.
        ("I2ABC", "IK1ABC", 0),
        ("I2ABC", "IS0ABC", 0),
        ("I2ABC", "IT9ABC", 0),
        # An Italian entrant: 1 within Europe, 3 outside it.
        ("I2ABC", "DL1ABC", 1),
        ("I2ABC", "OK2ABC", 1),
        ("I2ABC", "W1AW", 3),
        # A DX entrant: Italy is 10, and Sardinia is IS, not IS0.
        ("K6GTE", "I2ABC", 10),
        ("K6GTE", "IS0ABC", 10),
        ("K6GTE", "IT9ABC", 10),
        # own country 0, same continent 1, different continent 3
        ("K6GTE", "W1AW", 0),
        ("K6GTE", "DL1ABC", 3),
        ("K6GTE", "VE3ABC", 1),
    ],
)
def test_points(mycall, hiscall, expected):
    assert ari_dx.points(_ctx(mycall, hiscall)) == expected


def test_dupe_scores_nothing():
    assert ari_dx.points(_ctx("K6GTE", "I2ABC", is_dupe=1)) == 0
