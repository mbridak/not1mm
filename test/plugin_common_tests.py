"""The shared contest-plugin helpers.

contest_time() decides which clock a windowed dupe rule counts from: the
contact's own timestamp when it has one - which is what a re-scored or
imported log needs - and the wall clock otherwise, for a contact being typed
in.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

from not1mm.lib import plugin_common


def _ctx(stamp):
    return SimpleNamespace(contact={"TS": stamp})


def test_contest_time_uses_the_contact_timestamp():
    assert plugin_common.contest_time(_ctx("2026-04-18 05:30:00")) == datetime(
        2026, 4, 18, 5, 30
    )


def test_contest_time_falls_back_to_now():
    before = datetime.now(UTC).replace(tzinfo=None)
    stamp = plugin_common.contest_time(_ctx(""))
    after = datetime.now(UTC).replace(tzinfo=None)
    assert before <= stamp <= after


def test_contest_time_ignores_an_unparsable_timestamp():
    before = datetime.now(UTC).replace(tzinfo=None)
    stamp = plugin_common.contest_time(_ctx("not a date"))
    after = datetime.now(UTC).replace(tzinfo=None)
    assert before <= stamp <= after
