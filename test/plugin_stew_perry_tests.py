"""Stew Perry Topband: the distance step and the power multiplier.

Reference:
  https://www.kkn.net/stew/stew_rules.html  (rules 5, 7)
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import stew_perry_topband as stew


def _ctx(grid, my_grid="DM13"):
    # other_1 is the entry widget, which is empty once a log is imported.
    return SimpleNamespace(
        contact_is_dupe=0,
        contact={"Exchange1": grid},
        station={"GridSquare": my_grid},
        other_1=SimpleNamespace(text=lambda: ""),
    )


def test_points_read_the_contact_not_the_entry_field():
    # The log's own grid, not whatever is in the entry widget.
    assert stew.points(_ctx("FN31")) == 8
    assert stew.points(_ctx("CM87")) == 2


def test_points_add_one_for_every_500_km(monkeypatch):
    # Rule 5's own example: 1750 km is four points.
    monkeypatch.setattr(stew, "distance", lambda ours, theirs: 1750)
    assert stew.points(_ctx("FN31")) == 4
    # Exactly 500 km earns the extra point too.
    monkeypatch.setattr(stew, "distance", lambda ours, theirs: 500)
    assert stew.points(_ctx("FN31")) == 2
    monkeypatch.setattr(stew, "distance", lambda ours, theirs: 499)
    assert stew.points(_ctx("FN31")) == 1


def test_a_duplicate_scores_nothing():
    ctx = _ctx("FN31")
    ctx.contact_is_dupe = 1
    assert stew.points(ctx) == 0


@pytest.mark.parametrize(
    "power,expected",
    [
        ("HIGH", 24),
        ("LOW", 36),
        ("QRP", 72),
    ],
)
def test_calc_score_applies_the_entrants_power(monkeypatch, power, expected):
    # Rule 7: 1.5x for low power, 3x for QRP, and nothing for high power.
    monkeypatch.setattr(stew, "get_points", lambda self: 24)
    ctx = SimpleNamespace(contest_settings={"PowerCategory": power})
    assert stew.calc_score(ctx) == expected
