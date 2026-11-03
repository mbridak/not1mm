"""Tests for the SAC multiplier rules (sections 8.1 and 8.2).

SAC counts multipliers differently depending on where *you* are, and the corpus
only carries one log per station type, so the prefix-number arithmetic is
pinned here instead.

  https://www.sactest.net/blog/scandinavian-activity-contest-2026-rules/
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup

from not1mm.plugins import sac_cw, sac_ssb

PLUGINS = [sac_cw, sac_ssb]


class FakeDatabase:
    """Just enough DataBase for show_mults()."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.current_contest = 1

    def fetch_all_contacts_asc(self):
        return self.contacts

    def fetch_country_band_count(self):
        return {
            "cb_count": len(
                {(c["CountryPrefix"], c["Band"]) for c in self.contacts}
            )
        }


def _ctx(contacts, mycall="K6GTE"):
    ctx = SimpleNamespace()
    ctx.station = {"Call": mycall}
    ctx.pref = {"contest": 1}
    ctx.cty_lookup = cty_lookup
    ctx.database = FakeDatabase(contacts)
    return ctx


@pytest.mark.parametrize("plugin", PLUGINS)
def test_aland_and_market_reef_are_scandinavian(plugin):
    """Rule 2 lists them, and cty.dat keys them OH0 and OJ0."""
    ctx = _ctx(
        [
            {"Call": "OH0ABC", "Band": 14.0, "CountryPrefix": "OH0", "WPXPrefix": "OH0"},
            {"Call": "OJ0ABC", "Band": 14.0, "CountryPrefix": "OJ0", "WPXPrefix": "OJ0"},
        ]
    )
    assert plugin.show_mults(ctx) == 2


@pytest.mark.parametrize("plugin", PLUGINS)
def test_prefix_number_is_the_multiplier_not_the_prefix(plugin):
    """Rule 8.2: SI3, SK3, SL3, SM3, 7S3 and 8S3 are one multiplier."""
    ctx = _ctx(
        [
            {"Call": "SM3ABC", "Band": 14.0, "CountryPrefix": "SM", "WPXPrefix": "SM3"},
            {"Call": "SI3ABC", "Band": 14.0, "CountryPrefix": "SM", "WPXPrefix": "SI3"},
            {"Call": "7S3ABC", "Band": 14.0, "CountryPrefix": "SM", "WPXPrefix": "7S3"},
        ]
    )
    assert plugin.show_mults(ctx) == 1


@pytest.mark.parametrize("plugin", PLUGINS)
def test_two_or_more_numbers_use_the_first_and_default_is_zero(plugin):
    """Rule 8.2: OZ150A counts for OZ1, LA/G3XYZ counts for LA0."""
    ctx = _ctx(
        [
            {"Call": "OZ150A", "Band": 14.0, "CountryPrefix": "OZ", "WPXPrefix": "OZ150"},
            {"Call": "LA/G3XYZ", "Band": 14.0, "CountryPrefix": "LA", "WPXPrefix": "LA0"},
        ]
    )
    assert plugin.show_mults(ctx) == 2


@pytest.mark.parametrize("plugin", PLUGINS)
def test_once_per_band_and_bear_island_is_svalbard(plugin):
    """Rule 8.2 is per band; cty.dat's separate "JW/b" row is still JW."""
    ctx = _ctx(
        [
            {"Call": "OH0ABC", "Band": 14.0, "CountryPrefix": "OH0", "WPXPrefix": "OH0"},
            {"Call": "OH0ABC", "Band": 7.0, "CountryPrefix": "OH0", "WPXPrefix": "OH0"},
            {"Call": "JW0ABC", "Band": 14.0, "CountryPrefix": "JW/b", "WPXPrefix": "JW0"},
            {"Call": "JW0ABC", "Band": 14.0, "CountryPrefix": "JW", "WPXPrefix": "JW0"},
        ]
    )
    # OH0 on two bands, plus one Svalbard multiplier
    assert plugin.show_mults(ctx) == 3


@pytest.mark.parametrize("plugin", PLUGINS)
def test_scandinavian_station_counts_entities_per_band(plugin):
    """Rule 8.1: each worked DXCC entity, once per band."""
    ctx = _ctx(
        [
            {"Call": "K6GTE", "Band": 14.0, "CountryPrefix": "K", "WPXPrefix": "K5"},
            {"Call": "K6GTE", "Band": 7.0, "CountryPrefix": "K", "WPXPrefix": "K5"},
            {"Call": "DL1ABC", "Band": 14.0, "CountryPrefix": "DL", "WPXPrefix": "DL1"},
        ],
        mycall="SM5XYZ",
    )
    assert plugin.show_mults(ctx) == 3


@pytest.mark.parametrize("plugin", PLUGINS)
def test_non_scandinavian_stations_do_not_count(plugin):
    """Only Scandinavian entities are multipliers for a non-Scandinavian."""
    ctx = _ctx(
        [
            {"Call": "DL1ABC", "Band": 14.0, "CountryPrefix": "DL", "WPXPrefix": "DL1"},
            {"Call": "K6GTE", "Band": 14.0, "CountryPrefix": "K", "WPXPrefix": "K5"},
        ]
    )
    assert plugin.show_mults(ctx) == 0
