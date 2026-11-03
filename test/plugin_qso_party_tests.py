"""The generic State QSO Party pair, checked against their docstrings.

Both say: "Contact via phone: 1 point / CW: 2 / digital: 2", "Multipliers:
County, State, or Country ... across all modes/bands", and the RST flavour's
exchange is "RST + County/State/Country".

Reference: the docstring of each plugin.
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import qso_party_rst, qso_party_sn

MODULES = [qso_party_rst, qso_party_sn]


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("SSB", 1),
        ("USB", 1),
        ("LSB", 1),
        ("FM", 1),
        ("AM", 1),
        ("CW", 2),
        ("CW-U", 2),
        ("CWR", 2),
        ("FT8", 2),
        ("FT4", 2),
        ("RTTY", 2),
        ("PSK31", 2),
        # anything the docstring does not name scores nothing
        ("SSTV", 0),
        ("", 0),
    ],
)
def test_points_follow_the_docstring(module, mode, expected):
    ctx = SimpleNamespace(contact_is_dupe=0, contact={"Mode": mode})
    assert module.points(ctx) == expected


@pytest.mark.parametrize("module", MODULES)
def test_a_duplicate_scores_nothing(module):
    ctx = SimpleNamespace(contact_is_dupe=1, contact={"Mode": "CW"})
    assert module.points(ctx) == 0


class _Field:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):  # noqa: N802
        self._text = text


@pytest.mark.parametrize(
    "mode,expected",
    [
        # phone is RS (two characters), CW and digital are RST (three)
        ("SSB", "59"),
        ("USB", "59"),
        ("LSB", "59"),
        ("FM", "59"),
        ("AM", "59"),
        ("CW", "599"),
        ("RTTY", "599"),
        ("FT8", "599"),
    ],
)
def test_rst_prefill_uses_the_live_mode(mode, expected):
    ctx = SimpleNamespace(
        radio_state={"mode": mode}, sent=_Field(), receive=_Field()
    )
    qso_party_rst.prefill(ctx)
    assert ctx.sent.text() == expected
    assert ctx.receive.text() == expected


def test_rst_prefill_needs_a_mode():
    ctx = SimpleNamespace(radio_state={"mode": ""}, sent=_Field(), receive=_Field())
    qso_party_rst.prefill(ctx)
    assert ctx.sent.text() == ""
    assert ctx.receive.text() == ""


def test_sn_prefill_fills_the_serial():
    ctx = SimpleNamespace(current_sn=7, sent=_Field())
    qso_party_sn.prefill(ctx)
    assert ctx.sent.text() == "007"
