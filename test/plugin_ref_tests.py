"""Point values for the REF contest (Coupe du REF).

The corpus runs a French and a foreign entrant, but not every branch - a
French station working another French station on a different continent, for
one - and the two tables are easy to transpose.

References:
  https://concours.r-e-f.org/contest/a-propos  (QSO Points)
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.lib.contest import load_contest

PLUGINS = ["ref_cw", "ref_ssb"]


def _ctx(mycall, hiscall, is_dupe=0):
    """Minimal fake main window for the contest's points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        station={"Call": mycall},
        contact={"Call": hiscall},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "mycall,hiscall,expected",
    [
        # A French entrant.
        ("F5ABC", "F6XYZ", 6),  # another French station, same continent
        ("F5ABC", "FG5ABC", 15),  # Guadeloupe is on another continent
        ("F5ABC", "DL1ABC", 1),
        ("F5ABC", "K6GTE", 2),
        # A foreign entrant: only French stations score.
        ("K6GTE", "F5ABC", 3),
        ("K6GTE", "FG5ABC", 1),  # Guadeloupe is in North America
        ("K6GTE", "DL1ABC", 0),
        ("K6GTE", "W1AW", 0),
        # A DOM/TOM entrant uses the French table too.
        ("FG5ABC", "F5ABC", 15),
        ("FG5ABC", "K6GTE", 1),
    ],
)
def test_points(plugin, mycall, hiscall, expected):
    assert load_contest(plugin, _ctx(mycall, hiscall)).points() == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_dupe_scores_nothing(plugin):
    assert load_contest(plugin, _ctx("F5ABC", "F6XYZ", is_dupe=1)).points() == 0


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "nr,expected",
    [
        # The key is the exchange in the log's own form: NR is an INTEGER
        # column, so an all-digit department comes back as a number, while a
        # DOM/TOM prefix (text) is upper-cased.
        ("75", 75),
        (75, 75),
        ("2A", "2A"),
        ("2a", "2A"),
        ("FG", "FG"),
    ],
)
def test_the_department_key(plugin, nr, expected):
    """A French station's exchange is the department/prefix multiplier."""
    contest = load_contest(plugin, _ctx("K6GTE", "F9AB"))
    assert contest.mult_value(1, {"CountryPrefix": "F", "NR": nr}) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_a_foreign_exchange_is_not_a_department(plugin):
    """Only a French station sends a department; a serial is not one."""
    contest = load_contest(plugin, _ctx("K6GTE", "DL1ABC"))
    assert contest.mult_value(1, {"CountryPrefix": "DL", "NR": "001"}) is None
    assert contest.mult_value(1, {"CountryPrefix": "F", "NR": ""}) is None


@pytest.mark.parametrize("plugin", PLUGINS)
@pytest.mark.parametrize(
    "mycall,prefix,expected",
    [
        # French entities are departments, not countries.
        ("F5ABC", "DL", "DL"),
        ("F5ABC", "K", "K"),
        ("F5ABC", "F", None),
        ("F5ABC", "FG", None),
        # A foreign entrant cannot claim the countries at all.
        ("K6GTE", "DL", None),
    ],
)
def test_the_country_key(plugin, mycall, prefix, expected):
    """Non-French DXCC countries count, for a French entrant only."""
    contest = load_contest(plugin, _ctx(mycall, "DL1ABC"))
    assert contest.mult_value(2, {"CountryPrefix": prefix}) == expected


@pytest.mark.parametrize("plugin", PLUGINS)
def test_the_sql_keys(plugin):
    """The SQL keys say the same thing as the Python ones."""
    french = load_contest(plugin, _ctx("F5ABC", "DL1ABC"))
    assert french.mult_sql(1) == (
        "CASE WHEN CountryPrefix LIKE 'F%' AND NR <> '' THEN NR END"
    )
    assert french.mult_sql(2) == (
        "CASE WHEN CountryPrefix <> '' AND CountryPrefix NOT LIKE 'F%' "
        "THEN CountryPrefix END"
    )
    foreign = load_contest(plugin, _ctx("K6GTE", "F5ABC"))
    assert foreign.mult_sql(2) is None
