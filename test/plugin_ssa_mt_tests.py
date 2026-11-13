"""Tests for the SSA Manadstest multiplier and exchange rules.

The corpus logs one locator per band per station, so the "first four
characters, once per band" key and the mode codes are pinned here instead.

  https://hfcontest.ssa.se/ssa-mt/regler.html
"""

import sqlite3
from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest

PLUGINS = ["ssa_mt_cw", "ssa_mt_ssb"]


class FakeDatabase:
    """A real SQLite log, so the class's multiplier SQL runs for real."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.current_contest = 1
        self.db = sqlite3.connect(":memory:")
        # VARCHAR gives the column TEXT affinity, as the application's schema
        # does, so an all-digit exchange still counts as text.
        self.db.execute("create table dxlog (ContestNR, Exchange1 VARCHAR(20), Band)")
        for contact in contacts:
            self.db.execute(
                "insert into dxlog values (?, ?, ?)",
                (1, contact.get("Exchange1", ""), contact.get("Band")),
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


def _ctx(contacts):
    ctx = SimpleNamespace()
    ctx.station = {"Call": "K6GTE"}
    ctx.pref = {"contest": 1}
    ctx.database = FakeDatabase(contacts)
    return ctx


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "dupe,expected",
    [(0, 2), (1, 0)],
)
def test_two_points_unless_a_dupe(plugin, dupe, expected):
    """Every valid QSO is worth two points."""
    ctx = _ctx([])
    ctx.contact_is_dupe = dupe
    assert load_contest(plugin, ctx).points() == expected


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "exchange,expected",
    [
        ("JP75XX", "JP75"),
        ("jp75xx", "JP75"),
        ("JP75", "JP75"),
        ("JP7", None),
        ("", None),
        (None, None),
    ],
)
def test_the_locator_square_is_the_key(plugin, exchange, expected):
    """The multiplier is the first four characters, upper-cased."""
    contest = load_contest(plugin, _ctx([]))
    assert contest.mult_value(1, {"Exchange1": exchange}) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_short_exchange_is_not_a_multiplier(plugin):
    """A locator square needs four characters; a shorter one is not a key."""
    ctx = _ctx(
        [
            {"Exchange1": "JP75XX", "Band": 3.5},
            {"Exchange1": "JO65AA", "Band": 3.5},
            {"Exchange1": "JP75XX", "Band": 7.0},
            {"Exchange1": "JP7", "Band": 3.5},
            {"Exchange1": "", "Band": 3.5},
        ]
    )
    # JP75 and JO65 on 3.5, JP75 on 7.0; the short and the empty rows drop out.
    assert load_contest(plugin, ctx).show_mults() == 3


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_repeated_square_counts_once_per_band(plugin):
    """Two locators in the same square are one multiplier on that band."""
    ctx = _ctx(
        [
            {"Exchange1": "JP75AA", "Band": 3.5},
            {"Exchange1": "JP75BB", "Band": 3.5},
        ]
    )
    assert load_contest(plugin, ctx).show_mults() == 1


@pytest.mark.parametrize("plugin", PLUGINS)
def test_the_sql_key_is_the_substring(plugin):
    """The declared key is the same expression the module counted."""
    sql = load_contest(plugin, _ctx([])).mult_sql(1)
    assert "SUBSTR(Exchange1, 1, 4)" in sql
    assert "LENGTH(Exchange1) >= 4" in sql


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "mode,expected",
    [
        ("CW", "CW"),
        ("CW-R", "CW"),
        ("USB", "PH"),
        ("AM", "PH"),
        ("RTTY", "DG"),
        ("PSK31", "DG"),
        ("FT8", "DG"),
        ("SSB", "SSB"),
    ],
)
def test_the_cabrillo_mode_codes(plugin, mode, expected):
    """The sponsor writes every digital mode DG, and AM is phone."""
    assert load_contest(plugin, _ctx([])).cabrillo_mode(mode) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_the_qso_line_pads_both_serials(plugin):
    """The serials are three digits and the two locators follow them."""
    contest = load_contest(plugin, _ctx([]))
    line = contest.cabrillo_qso_line(
        {
            "TS": "2026-09-13 14:00:00",
            "Mode": "CW",
            "Freq": 3525,
            "StationPrefix": "K6GTE",
            "SNT": "599",
            "SentNr": 1,
            "GridSquare": "",
            "Call": "SM3ABC",
            "RCV": "599",
            "NR": "01",
            "Exchange1": "JP75",
        }
    )
    assert (
        line
        == "QSO:  3525 CW 2026-09-13 1400 K6GTE         599 001        SM3ABC        599 001 JP75"
    )


@pytest.mark.parametrize(
    "plugin,rst,valid",
    [
        ("ssa_mt_cw", "599", True),
        ("ssa_mt_cw", "111", True),
        ("ssa_mt_cw", "59", False),
        ("ssa_mt_cw", "600", False),
        ("ssa_mt_ssb", "59", True),
        ("ssa_mt_ssb", "11", True),
        ("ssa_mt_ssb", "599", False),
        ("ssa_mt_ssb", "09", False),
    ],
)
def test_the_rst_bounds_follow_the_mode(plugin, rst, valid):
    """The module's validation table keeps the mode's own report range."""
    module = __import__(f"not1mm.plugins.{plugin}", fromlist=["_check_rst"])
    assert module._check_rst(rst) is valid


@pytest.mark.parametrize("plugin", PLUGINS)
def test_the_locator_check(plugin):
    """A locator is six characters, from a Swedish contest square, and letters."""
    module = __import__(f"not1mm.plugins.{plugin}", fromlist=["_check_locator"])
    assert module._check_locator("JP75XX") is True
    assert module._check_locator("jp75xx") is True
    assert module._check_locator("JP75X") is False
    assert module._check_locator("AA00XX") is False
    assert module._check_locator("JP7512") is False
