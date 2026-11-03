"""The AGCW QRP Contest power-class point matrix.

The corpus walks the whole matrix, but the two combinations that differ from
the default are worth pinning on their own.

Reference:
  https://www.agcw.de/contest/qrp/qrp-c-engl  (rule 6)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins.agcw_qrp import points


def _ctx(ours, nr):
    return SimpleNamespace(
        contest_settings={"PowerCategory": ours},
        contact={"NR": nr},
        contact_is_dupe=0,
    )


@pytest.mark.parametrize(
    "ours,nr,expected",
    [
        # QRO against QRO scores nothing - and the setting is stored as
        # "HIGH", which used to be compared to "High".
        ("HIGH", "001/QRO/2345", 0),
        ("HIGH", "002/QRP/2345", 2),
        ("HIGH", "003/MP/NM", 2),
        ("HIGH", "004/VLP/2345", 2),
        # MP is "LOW" in the dialog: two points against everything.
        ("LOW", "001/QRO/2345", 2),
        ("LOW", "002/QRP/2345", 2),
        ("LOW", "003/MP/NM", 2),
        ("LOW", "004/VLP/2345", 2),
        # QRP scores three only against QRP and VLP.
        ("QRP", "001/QRO/2345", 2),
        ("QRP", "002/QRP/2345", 3),
        ("QRP", "003/MP/NM", 2),
        ("QRP", "004/VLP/2345", 3),
    ],
)
def test_power_class_points(ours, nr, expected):
    assert points(_ctx(ours, nr)) == expected


def test_an_empty_exchange_does_not_crash():
    # An unparsable exchange is assumed to be QRO.  This used to raise
    # NameError: pwr_class was only bound inside the "there is an exchange"
    # branch and then read outside it.
    assert points(_ctx("HIGH", "")) == 0
    assert points(_ctx("QRP", "")) == 2


def test_a_duplicate_scores_nothing():
    ctx = _ctx("QRP", "002/QRP/2345")
    ctx.contact_is_dupe = 1
    assert points(ctx) == 0
