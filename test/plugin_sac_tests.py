"""Tests for the SAC multiplier rules (sections 8.1 and 8.2).

SAC counts multipliers differently depending on where *you* are, and the corpus
only carries one log per station type, so the prefix-number arithmetic is
pinned here instead.

  https://www.sactest.net/blog/scandinavian-activity-contest-2026-rules/
"""

import sqlite3
from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup

from not1mm.lib.contest import load_contest

PLUGINS = ["sac_cw", "sac_ssb"]


class FakeDatabase:
    """A real SQLite log, so the class's multiplier SQL runs for real."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.current_contest = 1
        self.db = sqlite3.connect(":memory:")
        self.db.execute("create table dxlog (ContestNR, CountryPrefix, WPXPrefix, Band)")
        for contact in contacts:
            self.db.execute(
                "insert into dxlog values (?, ?, ?, ?)",
                (
                    1,
                    contact.get("CountryPrefix"),
                    contact.get("WPXPrefix"),
                    contact.get("Band"),
                ),
            )

    def fetch_mult_key_count(self, expression, per=()):
        """The base's count, over the in-memory log."""
        key = expression
        for column in per:
            key += f" || ':' || {column}"
        row = self.db.execute(
            f"select count(DISTINCT {key}) from dxlog where ContestNR = ?",
            (self.current_contest,),
        ).fetchone()
        return {"count": row[0]}

    def fetch_all_contacts_asc(self):
        return self.contacts

    def change_contact(self, contact):
        pass


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
    assert load_contest(plugin, ctx).show_mults() == 2


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
    assert load_contest(plugin, ctx).show_mults() == 1


@pytest.mark.parametrize("plugin", PLUGINS)
def test_two_or_more_numbers_use_the_first_and_default_is_zero(plugin):
    """Rule 8.2: OZ150A counts for OZ1, LA/G3XYZ counts for LA0."""
    ctx = _ctx(
        [
            {"Call": "OZ150A", "Band": 14.0, "CountryPrefix": "OZ", "WPXPrefix": "OZ150"},
            {"Call": "LA/G3XYZ", "Band": 14.0, "CountryPrefix": "LA", "WPXPrefix": "LA0"},
        ]
    )
    assert load_contest(plugin, ctx).show_mults() == 2


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
    assert load_contest(plugin, ctx).show_mults() == 3


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
    assert load_contest(plugin, ctx).show_mults() == 3


@pytest.mark.parametrize("plugin", PLUGINS)
def test_non_scandinavian_stations_do_not_count(plugin):
    """Only Scandinavian entities are multipliers for a non-Scandinavian."""
    ctx = _ctx(
        [
            {"Call": "DL1ABC", "Band": 14.0, "CountryPrefix": "DL", "WPXPrefix": "DL1"},
            {"Call": "K6GTE", "Band": 14.0, "CountryPrefix": "K", "WPXPrefix": "K5"},
        ]
    )
    assert load_contest(plugin, ctx).show_mults() == 0


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "mycall,contact,expected",
    [
        # A Scandinavian entrant keys on the entity.
        ("SM5XYZ", {"CountryPrefix": "DL", "WPXPrefix": "DL1"}, "DL"),
        # Everyone else keys on the entity and the prefix number.
        ("K6GTE", {"CountryPrefix": "SM", "WPXPrefix": "SM3"}, "SM:3"),
        ("K6GTE", {"CountryPrefix": "JW/b", "WPXPrefix": "JW0"}, "JW:0"),
        ("K6GTE", {"CountryPrefix": "DL", "WPXPrefix": "DL1"}, None),
        # A spot carries no CountryPrefix; the call answers it, and with no
        # WPXPrefix the area is empty, as str(None)[2:3] was.
        ("K6GTE", {"CountryPrefix": "", "Call": "SM5XYZ"}, "SM:"),
    ],
)
def test_the_multiplier_key(plugin, mycall, contact, expected):
    """The Python key is the same one the SQL counts."""
    ctx = _ctx([], mycall=mycall)
    assert load_contest(plugin, ctx).mult_value(1, contact) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_the_side_decides_the_sql_key(plugin):
    """A Scandinavian entrant's key is the column; everyone else's is a CASE."""
    assert load_contest(plugin, _ctx([], mycall="SM5XYZ")).mult_sql(1) == "CountryPrefix"
    sql = load_contest(plugin, _ctx([], mycall="K6GTE")).mult_sql(1)
    assert sql.startswith("CASE WHEN CountryPrefix = 'JW/b'")
    assert "'OH0'" in sql
    assert "substr(WPXPrefix, 3, 1)" in sql


@pytest.mark.parametrize("plugin", PLUGINS)
def test_nothing_is_marked(plugin):
    """The module never wrote IsMultiplierN; the class keeps that."""
    contacts = [
        {"Call": "OK2ABC", "Band": 14.0, "CountryPrefix": "OK", "WPXPrefix": "OK2"},
    ]
    ctx = _ctx(contacts, mycall="SM5XYZ")
    load_contest(plugin, ctx).recalculate_mults()
    assert "IsMultiplier1" not in contacts[0]
