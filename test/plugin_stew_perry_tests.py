"""Stew Perry Topband: the distance step and the power multiplier.

Reference:
  https://www.kkn.net/stew/stew_rules.html  (rules 5, 7)
"""

from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest

PLUGIN = "not1mm.plugins.stew_perry_topband"


def _ctx(grid, my_grid="DM13"):
    # NR is the logged exchange; the entry widget is empty once a log is
    # imported, so the points have to come from the contact.
    return SimpleNamespace(
        contact_is_dupe=0,
        contact={"NR": grid},
        station={"GridSquare": my_grid},
        other_1=SimpleNamespace(text=lambda: ""),
    )


def test_points_read_the_contact_not_the_entry_field():
    # The log's own grid, not whatever is in the entry widget.
    assert load_contest("stew_perry_topband", _ctx("FN31")).points() == 8
    assert load_contest("stew_perry_topband", _ctx("CM87")).points() == 2


def test_points_add_one_for_every_500_km(monkeypatch):
    # Rule 5's own example: 1750 km is four points.
    monkeypatch.setattr(f"{PLUGIN}.distance", lambda ours, theirs: 1750)
    assert load_contest("stew_perry_topband", _ctx("FN31")).points() == 4
    # Exactly 500 km earns the extra point too.
    monkeypatch.setattr(f"{PLUGIN}.distance", lambda ours, theirs: 500)
    assert load_contest("stew_perry_topband", _ctx("FN31")).points() == 2
    monkeypatch.setattr(f"{PLUGIN}.distance", lambda ours, theirs: 499)
    assert load_contest("stew_perry_topband", _ctx("FN31")).points() == 1


def test_a_duplicate_scores_nothing():
    ctx = _ctx("FN31")
    ctx.contact_is_dupe = 1
    assert load_contest("stew_perry_topband", ctx).points() == 0


@pytest.mark.parametrize(
    "power,expected",
    [
        ("HIGH", 24),
        ("LOW", 36),
        ("QRP", 72),
    ],
)
def test_calc_score_applies_the_entrants_power(power, expected):
    # Rule 7: 1.5x for low power, 3x for QRP, and nothing for high power.
    ctx = SimpleNamespace(
        contest_settings={"PowerCategory": power},
        database=SimpleNamespace(fetch_points=lambda: {"Points": 24}),
    )
    assert load_contest("stew_perry_topband", ctx).calc_score() == expected
