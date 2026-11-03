"""The Remembrance Day Contest's mode grouping and its triple-point window.

The corpus exercises both, but the grouping and the two boundaries are the
kind of decision worth pinning on their own.

References:
  https://www.wia.org.au/members/contests/rdcontest/  (rules 9.3, 10)
"""

import os
import time
from types import SimpleNamespace

import pytest

from not1mm.plugins.wia_remembrance import _dupe_mode, points


@pytest.fixture
def utc_tz():
    """Run a test at UTC and put the machine's zone back afterwards.

    points() reads the 0100-0600 window off the *local* clock (rule 10.5), so
    a test that pins a time has to pin the zone too.  The harness does this
    for the whole corpus; this is the small version for one test.
    """
    original = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


@pytest.mark.parametrize(
    "mode,group",
    [
        # Rule 9.3a: FM and SSB count as one mode, CW and RTTY as another.
        ("SSB", "PH"),
        ("USB", "PH"),
        ("LSB", "PH"),
        ("FM", "PH"),
        ("AM", "PH"),
        ("CW", "CW"),
        ("CW-U", "CW"),
        ("RTTY", "CW"),
        ("RTTY-R", "CW"),
        # anything else is its own group
        ("FT8", "FT8"),
        ("FT4", "FT4"),
    ],
)
def test_mode_grouping(mode, group):
    assert _dupe_mode(mode) == group


def _ctx(band, mode, time_on, dupe=0):
    """Minimal fake `self` for points()."""
    return SimpleNamespace(
        contact={
            "Band": band,
            "Mode": mode,
            "TS": f"2026-08-08 {time_on}",
        },
        contact_is_dupe=dupe,
    )


@pytest.mark.parametrize(
    "band,mode,time_on,expected",
    [
        # 160m doubles and the window triples, on top of CW doubling
        (1.8, "CW", "02:00:00", 12),
        # 23cm doubles too
        (1296.0, "CW", "03:00:00", 12),
        (3.5, "SSB", "02:05:00", 3),
        (3.5, "SSB", "07:00:00", 1),
        (7.0, "RTTY", "08:00:00", 2),
        # 160m alone is 4 outside the window and 12 inside it - the band was
        # compared to the string "1.8" and never got its extra point
        (1.8, "CW", "00:59:00", 4),
        (1.8, "CW", "06:01:00", 4),
        # the window is inclusive at both ends
        (1.8, "CW", "01:00:00", 12),
        (1.8, "CW", "06:00:00", 12),
    ],
)
def test_points(utc_tz, band, mode, time_on, expected):
    assert points(_ctx(band, mode, time_on)) == expected


def test_a_duplicate_scores_nothing(utc_tz):
    assert points(_ctx(1.8, "CW", "02:00:00", dupe=1)) == 0
