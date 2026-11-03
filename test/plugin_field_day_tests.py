"""Point values for the field-day family.

The contest corpus (test/contest_logs_test.py) only carries CW and SSB
contacts, so it cannot tell the old substring-based mode test apart from the
fixed one.  These tests pin the per-mode point values directly.

References:
  ARRL Field Day    https://contests.arrl.org/ContestRules/Field-Day-Rules.pdf
                    7.1.1 Phone 1 point, 7.1.2 CW 2 points, 7.1.3 Digital 2 points
  Winter Field Day  https://winterfieldday.org/downloads/2026-rules-v3.pdf
                    Phone 1 point, CW and digital 2 points; FT4 and FT8 are excluded
"""

from types import SimpleNamespace

import pytest

from not1mm.plugins import arrl_field_day, winter_field_day


def _ctx(mode="CW", is_dupe=0):
    """Minimal fake `self` for points()."""
    return SimpleNamespace(contact_is_dupe=is_dupe, contact={"Mode": mode})


@pytest.mark.parametrize("mode", ["SSB", "USB", "LSB", "FM", "AM", "PH", "ssb"])
def test_arrl_field_day_phone_is_one_point(mode):
    assert arrl_field_day.points(_ctx(mode)) == 1


@pytest.mark.parametrize("mode", ["CW", "RTTY", "FT8", "FT4", "PSK31", "OLIVIA", "JS8"])
def test_arrl_field_day_cw_and_digital_are_two_points(mode):
    assert arrl_field_day.points(_ctx(mode)) == 2


def test_arrl_field_day_empty_mode_scores_nothing():
    assert arrl_field_day.points(_ctx("")) == 0


def test_arrl_field_day_dupe_scores_nothing():
    assert arrl_field_day.points(_ctx("CW", is_dupe=1)) == 0


@pytest.mark.parametrize("mode", ["SSB", "USB", "LSB", "FM", "AM", "PH"])
def test_winter_field_day_phone_is_one_point(mode):
    assert winter_field_day.points(_ctx(mode)) == 1


@pytest.mark.parametrize("mode", ["CW", "RTTY", "PSK31", "OLIVIA", "JS8"])
def test_winter_field_day_cw_and_digital_are_two_points(mode):
    assert winter_field_day.points(_ctx(mode)) == 2


@pytest.mark.parametrize("mode", ["FT4", "FT8"])
def test_winter_field_day_ft4_ft8_score_nothing(mode):
    assert winter_field_day.points(_ctx(mode)) == 0


def test_winter_field_day_empty_mode_scores_nothing():
    assert winter_field_day.points(_ctx("")) == 0


def test_winter_field_day_dupe_scores_nothing():
    assert winter_field_day.points(_ctx("CW", is_dupe=1)) == 0
