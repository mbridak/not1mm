"""Multiplier handling for the URE EA contests.

The corpus works only non-Spanish stations from a US log and a Spanish one, so
it cannot exercise the call areas cty.dat reports as entities of their own, nor
the split the online score feed asks for.

References:
  https://concursos.ure.es/en/eartty/bases/  (Multipliers)
  https://concursos.ure.es/en/s-m-el-rey-de-espana-cw/bases/  (Multipliers)
"""

import uuid
from pathlib import Path

import pytest

import not1mm
from not1mm.lib.database import DataBase

from not1mm.plugins import ea_majestad_cw, ea_rtty

PLUGINS = [ea_majestad_cw, ea_rtty]


class Harness:
    """Just enough of MainWindow to log contacts and read the multipliers."""

    def __init__(self, plugin, tmp_path):
        self.plugin = plugin
        self.database = DataBase(
            str(tmp_path / "t.db"),
            Path(not1mm.__file__).parent / "data",
            current_contest=1,
        )
        self.contact = {}

    def log(self, call, band="14.0", country_prefix="", wpx="", nr=""):
        contact = self.database.empty_contact.copy()
        contact.update(
            {
                "ID": uuid.uuid4().hex,
                "TS": "2026-04-04 12:00:00",
                "Call": call,
                "Band": band,
                "Freq": 14070.0,
                "Mode": "RTTY",
                "ContestNR": 1,
                "CountryPrefix": country_prefix,
                "WPXPrefix": wpx,
                "NR": nr,
            }
        )
        self.database.log_contact(contact)


@pytest.fixture
def h(tmp_path):
    return Harness(ea_rtty, tmp_path)


def test_call_areas_include_alaska_and_hawaii(h):
    """cty.dat reports KH6 and KL as entities of their own, but they are US
    call areas."""
    h.log("W1AW", country_prefix="K", wpx="W1", nr="001")
    h.log("KH6ABC", country_prefix="KH6", wpx="KH6", nr="002")
    h.log("KL7ABC", country_prefix="KL", wpx="KL7", nr="003")
    # three call areas plus the three entities
    assert h.plugin.show_mults(h) == 6


def test_area_falls_back_to_the_callsign(h):
    """A log imported without a WPX prefix still gives up the area."""
    h.log("KH6ABC", country_prefix="KH6", nr="001")
    # one call area plus one entity
    assert h.plugin.show_mults(h) == 2


def test_area_is_the_digit_of_the_prefix(h):
    """K1A and K2A are areas 1 and 2, though both prefixes end in A."""
    h.log("K1A", country_prefix="K", wpx="K1A", nr="001")
    h.log("K2A", country_prefix="K", wpx="K2A", nr="002")
    # two call areas plus the one K entity
    assert h.plugin.show_mults(h) == 3


def test_only_the_four_countries_have_call_areas():
    assert {"K", "KL", "KH6", "KP4", "VE", "VK", "JA"} <= ea_rtty.CALL_AREA_PREFIXES
    assert "PY" not in ea_rtty.CALL_AREA_PREFIXES
    assert "EA" not in ea_rtty.CALL_AREA_PREFIXES


@pytest.mark.parametrize("plugin", PLUGINS)
def test_rtc_split_adds_up(plugin, tmp_path):
    """The online score feed gets a country/state split that totals right."""
    harness = Harness(plugin, tmp_path)
    harness.log("EA4ABC", country_prefix="EA", wpx="EA4", nr="M")
    harness.log("W1AW", country_prefix="K", wpx="W1")
    harness.log("DL1ABC", country_prefix="DL", wpx="DL")
    country, state = plugin.show_mults(harness, rtc=True)
    assert (country, state) != (0, 0)
    assert country + state == plugin.show_mults(harness)
