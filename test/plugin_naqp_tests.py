"""Point values for the North American QSO Party.

The corpus works NA and non-NA stations from a US station and a German one, so
it cannot exercise the "addition of Hawaii" in the definition of a North
American station: cty.dat files KH6 under Oceania.  Pin the point values here.

Reference:
  https://ncjweb.com/NAQP-Rules.pdf
  ("North American Station: Defined by the ARRL DXCC List, with the addition of
  Hawaii.")
"""

from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup

from not1mm.plugins import naqp_cw, naqp_rtty, naqp_ssb

PLUGINS = [naqp_cw, naqp_ssb, naqp_rtty]


def _ctx(my_call, his_call, is_dupe=0):
    """Minimal fake `self` for points()."""
    return SimpleNamespace(
        contact_is_dupe=is_dupe,
        contact={"Call": his_call},
        station={"Call": my_call},
        cty_lookup=cty_lookup,
    )


@pytest.mark.parametrize("module", PLUGINS)
@pytest.mark.parametrize(
    "my_call,his_call,expected",
    [
        ("K6GTE", "W1AW", 1),  # NA - NA
        ("K6GTE", "DL1ABC", 1),  # NA - non-NA
        ("DL1ABC", "W1AW", 1),  # non-NA - NA
        ("KH6XYZ", "W1AW", 1),  # Hawaii counts as North America
        ("KH6XYZ", "DL1ABC", 1),  # ... even against a non-NA station
        ("DL1ABC", "KH6XYZ", 1),  # ... and from the other side of the QSO
        ("KL7XYZ", "DL1ABC", 1),  # Alaska is already NA in cty.dat
        ("DL1ABC", "JA1ABC", 0),  # non-NA - non-NA
        ("JA1ABC", "PY1ABC", 0),
    ],
)
def test_naqp_points(module, my_call, his_call, expected):
    assert module.points(_ctx(my_call, his_call)) == expected


@pytest.mark.parametrize("module", PLUGINS)
def test_naqp_dupe_scores_nothing(module):
    assert module.points(_ctx("K6GTE", "W1AW", is_dupe=1)) == 0


class FakeLineEdit:
    """Stands in for a QLineEdit."""

    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text


class FakeDatabase:
    """Just enough DataBase for set_contact_vars()."""

    def __init__(self, current_contest=1, seen=()):
        self.current_contest = current_contest
        self.seen = set(seen)

    def exec_sql(self, query, params=None):
        key, band, _contest = params
        return {"mult_count": 1 if (key, band) in self.seen else 0}


def _entry_ctx(his_call, sect, band="7.0", seen=()):
    """Minimal fake `self` for set_contact_vars()."""
    return SimpleNamespace(
        contact={"Call": his_call, "Band": band},
        sent=FakeLineEdit("599"),
        receive=FakeLineEdit("599"),
        other_1=FakeLineEdit("DAVE"),
        other_2=FakeLineEdit(sect),
        station={"Call": "K6GTE"},
        cty_lookup=cty_lookup,
        contest_settings={"SentExchange": "MIKE CA"},
        database=FakeDatabase(seen=seen),
    )


@pytest.mark.parametrize("module", PLUGINS)
@pytest.mark.parametrize(
    "his_call,sect,expected",
    [
        ("W1AW", "TX", "TX"),  # a US state is its own multiplier
        ("VE3AA", "ON", "ON"),  # and so is a VE province
        ("KH6AA", "HI", "HI"),  # Hawaii counts as a state
        ("KH6AA", "KH6", "HI"),  # ... even when the prefix is sent
        ("KL7AA", "AK", "AK"),  # so does Alaska
        ("KP4AA", "PR", "C-KP4"),  # other NA entities key on the country
        ("XE1AA", "XE", "C-XE"),
        ("VP9AA", "VP9", "C-VP9"),
        ("HI8AA", "DR", "C-HI"),  # Dominican Republic, not Hawaii
        ("DL1AA", "DX", ""),  # outside North America: not a multiplier
        ("JA1AA", "DX", ""),
        ("W1AW", "ZZ", ""),  # a location that is not a multiplier
        ("W1AW", "", ""),  # ... nor a missing one
    ],
)
def test_naqp_multiplier_key(module, his_call, sect, expected):
    ctx = _entry_ctx(his_call, sect)
    module.set_contact_vars(ctx)
    assert ctx.contact["Exchange1"] == expected


@pytest.mark.parametrize("module", PLUGINS)
def test_naqp_new_multiplier_is_marked(module):
    ctx = _entry_ctx("W1AW", "TX")
    module.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 1


@pytest.mark.parametrize("module", PLUGINS)
def test_naqp_repeated_multiplier_is_not_marked(module):
    ctx = _entry_ctx("W1AW", "TX", seen=[("TX", "7.0")])
    module.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 0


@pytest.mark.parametrize("module", PLUGINS)
def test_naqp_non_multiplier_is_not_marked(module):
    ctx = _entry_ctx("DL1AA", "DX")
    module.set_contact_vars(ctx)
    assert ctx.contact["IsMultiplier1"] == 0
