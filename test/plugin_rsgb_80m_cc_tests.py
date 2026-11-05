"""Scoring rules for the RSGB 3.5MHz Club Championship (80m CC).

Rule 6: "A UK&CD station is required to be at one or both ends of a contact for
it to count for points", and "An RSGB station (G6XX or a regional variant) ...
QSOs with this station will be worth 5 QSO points."

The corpus works either non-UK stations from the US log or UK-to-non-UK from
the G3XYZ log, so the five-point case has to be pinned here.

References:
  https://www.rsgbcc.org/hf/rules/2026/r80mcc.shtml  (rule 6)
  https://rsgb.org/main/radio-sport/rsgb-contest-club
  ("G6XX and its regional variants (GD6XX, GI6XX, GJ6XX, GM6XX, GU6XX, and
  GW6XX)")
"""

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import not1mm
from not1mm.lib.database import DataBase

from contest_harness import cty_lookup

from not1mm.plugins import rsgb_80m_cc


def _ctx(my_call, his_call, is_dupe=0):
    """Minimal fake `self` for points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        contact={"Call": his_call},
        station={"Call": my_call},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize(
    "my_call,his_call,expected",
    [
        ("G3XYZ", "W1AW", 1),  # UK&CD at one end
        ("W1AW", "G3XYZ", 1),  # ... from either end
        ("G3XYZ", "GM0ABC", 1),
        ("GW0ABC", "MW0ABC", 1),  # GW and MW are both Wales
        ("M0ABC", "2E0ABC", 1),  # both England
        ("EI2ABC", "MW0ABC", 1),  # EI is not UK&CD, but MW is
        ("K6GTE", "DL1ABC", 0),  # neither end is UK&CD
        ("K6GTE", "EI2ABC", 0),
        ("EI2ABC", "DL1ABC", 0),
    ],
)
def test_ukcd_at_one_end_is_required(my_call, his_call, expected):
    assert rsgb_80m_cc.points(_ctx(my_call, his_call)) == expected


@pytest.mark.parametrize(
    "call",
    ["G6XX", "G6XX/P", "GW6XX", "MW6XX", "GM6XX", "MM6XX", "GD6XX", "MD6XX"],
)
def test_society_station_scores_five(call):
    assert rsgb_80m_cc.points(_ctx("G3XYZ", call)) == 5


@pytest.mark.parametrize("call", ["M6XX", "G3XYZ", "GW3XYZ", "G6ZZ", "W6XX"])
def test_other_stations_score_one(call):
    assert rsgb_80m_cc.points(_ctx("G3XYZ", call)) == 1


@pytest.mark.parametrize(
    "call", ["G6XX", "G6XX/P", "GW6XX", "MW6XX", "MM6XX", "MD6XX", "GE6XX", "ME6XX"]
)
def test_is_rsgb_station(call):
    assert rsgb_80m_cc.is_rsgb_station(call)


@pytest.mark.parametrize("call", ["M6XX", "G3XYZ", "GW3XYZ", "W6XX", ""])
def test_is_not_rsgb_station(call):
    assert not rsgb_80m_cc.is_rsgb_station(call)


def test_dupe_scores_nothing():
    assert rsgb_80m_cc.points(_ctx("G3XYZ", "W1AW", is_dupe=1)) == 0


class Harness:
    """Just enough of MainWindow to log contacts and ask for a dupe verdict."""

    def __init__(self, tmp_path, mycall="G3XYZ"):
        self.plugin = rsgb_80m_cc
        self.database = DataBase(
            str(tmp_path / "t.db"),
            Path(not1mm.__file__).parent / "data",
            current_contest=1,
        )
        self.station = {"Call": mycall}
        self.contact = {}
        self.radio_state = {"mode": ""}
        self.contact_is_dupe = 0

    def log(self, call, mode, band="3.5"):
        self.contact = self.database.empty_contact.copy()
        self.contact.update(
            {
                "ID": uuid.uuid4().hex,
                "TS": "2026-02-12 20:00:00",
                "Call": call,
                "Band": band,
                "Freq": 3520.0,
                "Mode": mode,
                "ContestNR": 1,
                "StationPrefix": self.station["Call"],
            }
        )
        self.database.log_contact(self.contact)

    def is_dupe(self, call, mode):
        self.radio_state = {"mode": mode}
        self.contact = {"Call": call, "Mode": mode}
        return rsgb_80m_cc.specific_contest_check_dupe(self, call)["isdupe"]


@pytest.fixture
def h(tmp_path):
    return Harness(tmp_path)


def test_rtty_and_psk_are_separate_modes(h):
    """Rule 6: "the same station may be worked once on PSK63 and once on RTTY"."""
    h.log("G4ABC", "RTTY")
    assert h.is_dupe("G4ABC", "RTTY")
    assert not h.is_dupe("G4ABC", "PSK31")
    assert not h.is_dupe("G4ABC", "PSK63")


def test_psk_before_rtty(h):
    h.log("G4ABC", "PSK63")
    assert h.is_dupe("G4ABC", "PSK31")
    assert not h.is_dupe("G4ABC", "RTTY")


def test_phone_spellings_are_one_mode(h):
    h.log("G4ABC", "LSB")
    assert h.is_dupe("G4ABC", "USB")
    assert h.is_dupe("G4ABC", "PH")
    assert not h.is_dupe("G4ABC", "CW")
    assert not h.is_dupe("G4ABC", "RTTY")


def test_cw_variants_are_one_mode(h):
    h.log("G4ABC", "CW")
    assert h.is_dupe("G4ABC", "CW-R")
    assert not h.is_dupe("G4ABC", "RTTY")


def test_other_stations_are_not_dupes(h):
    h.log("G4ABC", "CW")
    assert not h.is_dupe("GM0ABC", "CW")
