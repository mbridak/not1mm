"""The migrated contests read their declared boxes by name.

A plugin that declares ``EntryWindowInfo`` reaches the entry window through
``parent.fields.<Box>``.  These cases pin the three things a migration can get
wrong: a box name the declaration does not have, a column that stops being
filled, and a report that disappears when its box is no longer shown.

They use the declaration itself to build the stand-in fields, so a name used in
the plugin but missing from ``EntryWindowInfo`` fails here rather than only in a
running window.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from contest_harness import cty_lookup
from not1mm.lib.contest import (
    MULT_KEYS,
    ContestBase,
    PLUGIN_PATH,
    load_contest,
)

SNAPSHOT = json.loads(
    (Path(__file__).parent / "data" / "contact_vars_snapshot.json").read_text(
        encoding="utf-8"
    )
)["plugins"]

# A direct copy: the box the old positional name held still feeds the same
# contact column.
STANDARD_SOURCES = {
    "SNT": "sent",
    "RCV": "receive",
    "SentNr": "other_1",
    "NR": "other_2",
}
SENTINELS = {"sent": "AA", "receive": "BB", "other_1": "CC", "other_2": "DD"}
BOXFORT = {
    "sent": "SNTText",
    "receive": "RCVText",
    "other_1": "SntNrText",
    "other_2": "RcvNrText",
}


def standard_plugins():
    """Migrated plugins whose mapping is still the old four direct copies."""
    standard_boxes = {"SNTText", "RCVText", "SntNrText", "RcvNrText"}
    names = []
    for name, data in SNAPSHOT.items():
        module = importlib.import_module(f"not1mm.plugins.{name}")
        if getattr(module.Contest, "EntryWindowInfo", None) is None:
            continue
        boxes = {box.spec.name for box in load_contest(name, None).entry_boxes()}
        if not standard_boxes <= boxes:
            continue
        if all(
            STANDARD_SOURCES.get(column) == spec.split(":", 1)[0]
            for column, spec in data["columns"].items()
        ):
            names.append(name)
    return sorted(names)


class FakeLineEdit:
    def __init__(self, text=""):
        self._text = text
        self.reads = 0

    def text(self):
        self.reads += 1
        return self._text

    def setText(self, text):  # noqa: N802
        self._text = text

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class FakeFields:
    """Only the boxes the contest declared; anything else is an error."""

    def __init__(self, boxes):
        object.__setattr__(
            self, "_edits", {box.spec.name: FakeLineEdit() for box in boxes}
        )
        object.__setattr__(self, "_specs", {box.spec.name: box.spec for box in boxes})

    def __getattr__(self, name):
        try:
            return self._edits[name]
        except KeyError:
            raise AttributeError(name) from None

    def __iter__(self):
        return (
            SimpleNamespace(spec=self._specs[name], edit=edit)
            for name, edit in self._edits.items()
        )


class FakeDatabase:
    def mult_key_exists(self, *args, **kwargs):
        return {"count": 0}

    def fetch_all_contacts_asc(self):
        return []

    def exec_sql(self, *args, **kwargs):
        return {"count": 0}

    def __getattr__(self, _name):
        return lambda *args, **kwargs: {}


def _run_fields(plugin, values, mode="CW", station=None):
    """Load *plugin*, fill *values*, log; return (contact, fields)."""
    contest = load_contest(plugin, None)
    boxes = contest.entry_boxes()
    declared = {box.spec.name for box in boxes}
    missing = set(values) - declared
    assert not missing, f"{plugin} has no {missing}; declared {sorted(declared)}"

    fields = FakeFields(boxes)
    for name, text in values.items():
        getattr(fields, name).setText(text)

    parent = SimpleNamespace(
        fields=fields,
        contact={"Call": "K1ABC", "Band": "7.0", "Mode": mode},
        contact_is_dupe=0,
        callsign=FakeLineEdit("K1ABC"),
        exch_label=FakeLineEdit(),
        history_info=FakeLineEdit(),
        station=station or {"Call": "K6GTE"},
        current_mode=mode,
        current_sn="1",
        pref={"contest": 1, "run_state": False},
        radio_state={"mode": mode},
        ctyfile={},
        contest_settings={"SentExchange": "03"},
        database=FakeDatabase(),
        cty_lookup=cty_lookup,
        show_message_box=lambda *_args, **_kwargs: None,
        log_window=None,
    )
    contest.parent = parent
    contest.set_contact_vars()
    return parent.contact, fields


def _run(plugin, values, mode="CW", station=None):
    """Load *plugin* with the boxes in *values* filled, then log the contact."""
    contact, _ = _run_fields(plugin, values, mode, station)
    return contact


def test_ari_dx_reads_the_plain_four_boxes():
    contact = _run(
        "ari_dx",
        {"SNTText": "599", "RCVText": "599", "SntNrText": "001", "RcvNrText": "rm"},
    )
    assert contact["SNT"] == "599"
    assert contact["RCV"] == "599"
    assert contact["SentNr"] == "001"
    assert contact["NR"] == "RM"


@pytest.mark.parametrize(
    "plugin,mode,report",
    [("naqp_cw", "CW", "599"), ("naqp_ssb", "SSB", "59"), ("naqp_rtty", "RTTY", "599")],
)
def test_naqp_has_no_report_box_but_still_logs_one(plugin, mode, report):
    contact = _run(plugin, {"NameText": "Dave", "SectText": "nc"}, mode=mode)
    assert contact["SNT"] == report
    assert contact["RCV"] == report
    assert contact["Name"] == "DAVE"
    assert contact["Sect"] == "NC"


def test_cq_ww_stores_the_zone_from_its_exchange_box():
    contact = _run(
        "cq_ww_cw", {"SNTText": "599", "RCVText": "599", "Exchange1Text": "15"}
    )
    assert contact["ZN"] == "15"
    # The old code also copied the zone into NR; the zone is not a serial.
    assert "NR" not in contact
    assert contact["SentNr"] == "03"


def test_ca_qso_party_serials_and_exchange():
    contact = _run(
        "ca_qso_party",
        {"SntNrText": "001", "RcvNrText": "002", "Exchange1Text": "CA"},
        station={"Call": "K6GTE", "State": "CA"},
    )
    assert contact["SentNr"] == "001"
    assert contact["NR"] == "002"
    assert contact["Exchange1"] == "CA"
    # The reports were never part of this contest's exchange.
    assert "SNT" not in contact or not contact["SNT"]


THREE_TWO = [
    "arrl_field_day",
    "winter_field_day",
    "arrl_vhf_jan",
    "arrl_vhf_jun",
    "arrl_vhf_sep",
    "cq_ww_vhf",
    "cwo",
    "cwt",
    "icwc_mst",
    "k1usn_sst",
    "na_sprint_cw",
    "na_sprint_rtty",
    "phone_weekly_test",
    "vhf_sprint",
    "weekly_rtty",
]


@pytest.mark.parametrize("plugin", THREE_TWO)
def test_the_two_box_family_declares_only_exchange_boxes(plugin):
    contest = load_contest(plugin, None)
    boxes = [box.spec.name for box in contest.entry_boxes()]
    assert len(boxes) == 2
    assert "SNTText" not in boxes and "RCVText" not in boxes
    assert contest.ESMExchangeField is None
    assert contest.NextField is None


@pytest.mark.parametrize(
    "plugin,values,column,expected",
    [
        (
            "arrl_field_day",
            {"Exchange1Text": "3a", "SectText": "org"},
            "Exchange1",
            "3A",
        ),
        ("arrl_field_day", {"Exchange1Text": "3a", "SectText": "org"}, "Sect", "ORG"),
        ("arrl_vhf_jan", {"SntNrText": "fn31", "RcvNrText": "em12"}, "NR", "EM12"),
        ("cwo", {"SntNrText": "001", "Exchange1Text": "123 bob"}, "Name", "BOB"),
        ("cwo", {"SntNrText": "001", "Exchange1Text": "123 bob"}, "NR", "123"),
        ("cwt", {"NameText": "bob", "RcvNrText": "123"}, "Name", "BOB"),
        ("icwc_mst", {"SntNrText": "001", "Exchange1Text": "bob 123"}, "Name", "BOB"),
        ("k1usn_sst", {"NameText": "bob", "SectText": "nc"}, "Sect", "NC"),
        ("phone_weekly_test", {"NameText": "bob", "SectText": "nc"}, "Name", "BOB"),
        ("weekly_rtty", {"NameText": "bob", "SectText": "nc"}, "Sect", "NC"),
    ],
)
def test_the_two_box_family_fills_its_columns(plugin, values, column, expected):
    contact = _run(plugin, values)
    assert contact[column] == expected


@pytest.mark.parametrize("plugin", ["cwo", "icwc_mst", "na_sprint_cw"])
def test_a_free_form_exchange_keeps_a_space(plugin):
    contest = load_contest(plugin, None)
    assert contest.SpaceKeepsFocus == ("Exchange1Text",)


LAST_GROUP = [
    "qso_party_rst",
    "qso_party_sn",
    "stew_perry_topband",
    "raem",
    "dxpedition",
]


@pytest.mark.parametrize("plugin", LAST_GROUP)
def test_the_last_group_is_migrated(plugin):
    contest = load_contest(plugin, None)
    boxes = [box.spec.name for box in contest.entry_boxes()]
    assert boxes
    assert contest.ESMExchangeField is None
    assert contest.NextField is None


@pytest.mark.parametrize(
    "plugin,values,column,expected",
    [
        (
            "qso_party_rst",
            {"SNTText": "599", "RCVText": "599", "Exchange1Text": "ca"},
            "Exchange1",
            "CA",
        ),
        (
            "qso_party_sn",
            {"SntNrText": "001", "RcvNrText": "002", "Exchange1Text": "ca"},
            "SentNr",
            "001",
        ),
        (
            "qso_party_sn",
            {"SntNrText": "001", "RcvNrText": "002", "Exchange1Text": "ca"},
            "NR",
            "002",
        ),
        (
            "stew_perry_topband",
            {"SNTText": "599", "RCVText": "599", "RcvNrText": "em12"},
            "NR",
            "EM12",
        ),
        (
            "raem",
            {"SntNrText": "001", "RcvNrText": "002", "Exchange1Text": "55N 37E"},
            "SentNr",
            "001",
        ),
        (
            "raem",
            {"SntNrText": "001", "RcvNrText": "002", "Exchange1Text": "55N 37E"},
            "Exchange1",
            "55N 37E",
        ),
    ],
)
def test_the_last_group_fills_its_columns(plugin, values, column, expected):
    contact = _run(plugin, values)
    assert contact[column] == expected


def _all_plugins():
    return sorted(
        path.stem
        for path in PLUGIN_PATH.glob("*.py")
        if path.stem not in {"__init__", "base"}
    )


def _value_for(plugin, spec):
    """A value that lets every contest read its box without crashing."""
    if plugin == "agcw_qrp" and spec.name == "RcvNrText":
        return "001 QRO 123"
    return {
        "SNTText": "599",
        "RCVText": "599",
        "SntNrText": "001",
        "RcvNrText": "01",
        "Exchange1Text": "AA",
        "MiscText": "AA",
        "SectText": "AA",
        "GridSquareText": "FN31",
        "NameText": "AA",
        "CommentText": "AA",
    }.get(spec.name, "AA")


@pytest.mark.parametrize("plugin", _all_plugins())
def test_every_declared_box_is_read_when_logging(plugin):
    """A declared box that logging never reads is a dead box."""
    boxes = load_contest(plugin, None).entry_boxes()
    values = {box.spec.name: _value_for(plugin, box.spec) for box in boxes}
    _, fields = _run_fields(plugin, values)
    for name, edit in fields._edits.items():
        assert edit.reads > 0, (plugin, name)


@pytest.mark.parametrize("plugin", _all_plugins())
def test_every_multiplier_key_is_known(plugin):
    contest = load_contest(plugin, None)
    for slot in (1, 2, 3):
        if slot > contest.NumMults:
            continue
        key = contest._mult_key(slot)
        if key is not None:
            assert key in MULT_KEYS, (plugin, slot, key)


CALL_DERIVED = {"CountryPrefix", "WPXPrefix", "CallSign", "LASTLETTER"}


@pytest.mark.parametrize("plugin", _all_plugins())
def test_a_multiplier_column_is_filled(plugin):
    """A column whose multiplier query the base builds must get a value."""
    contest = load_contest(plugin, None)
    if not contest.NumMults or contest.mult_sql is not ContestBase.mult_sql:
        return
    boxes = contest.entry_boxes()
    values = {box.spec.name: _value_for(plugin, box.spec) for box in boxes}
    contact, _ = _run_fields(plugin, values)
    for slot, _name, key, _per in contest._mult_slots():
        if key in CALL_DERIVED:
            continue
        entry = MULT_KEYS.get(key)
        assert entry is not None, (plugin, slot, key)
        sql = entry[0]
        column = sql[7:].split(",")[0] if sql.startswith("substr(") else sql
        assert contact.get(column), (plugin, slot, key, column)


THREE_BOX = [
    "10_10_fall_cw",
    "10_10_spring_cw",
    "10_10_summer_phone",
    "10_10_winter_phone",
    "ari_40_80",
    "arrl_160m",
    "arrl_dx_cw",
    "arrl_dx_ssb",
    "cq_160_cw",
    "cq_160_ssb",
    "cqws",
    "euhfc",
    "iaru_hf",
]


@pytest.mark.parametrize("plugin", THREE_BOX)
def test_the_three_box_family_has_one_received_exchange(plugin):
    contest = load_contest(plugin, None)
    assert [box.spec.name for box in contest.entry_boxes()] == [
        "SNTText",
        "RCVText",
        "Exchange1Text",
    ]
    assert contest.esm_field_name() == "Exchange1Text"
    assert contest.next_field_name() == "Exchange1Text"
    cls = importlib.import_module(f"not1mm.plugins.{plugin}").Contest
    assert "process_esm" not in cls.__dict__


@pytest.mark.parametrize(
    "plugin,value,column,expected",
    [
        ("10_10_fall_cw", "Dave 1234 NC", "NR", "DAVE 1234 NC"),
        ("ari_40_80", "ab123", "NR", "AB123"),
        ("arrl_160m", "org", "Exchange1", "org"),
        ("arrl_dx_cw", "100", "NR", "100"),
        ("cq_160_cw", "org", "NR", "org"),
        ("cqws", "single-op", "NR", "single-op"),
        ("euhfc", "82", "NR", "82"),
        ("iaru_hf", "28", "ZN", "28"),
    ],
)
def test_the_three_box_family_still_fills_the_same_column(
    plugin, value, column, expected
):
    contact = _run(
        plugin,
        {"SNTText": "599", "RCVText": "599", "Exchange1Text": value},
    )
    assert contact[column] == expected


@pytest.mark.parametrize("plugin", standard_plugins())
def test_a_standard_contest_keeps_its_old_box_to_column_mapping(plugin):
    """Every direct copy in the pre-refactor snapshot is still a direct copy."""
    values = {BOXFORT[source]: text for source, text in SENTINELS.items()}
    contact = _run(plugin, values)
    expected = SNAPSHOT[plugin]["columns"]
    assert expected
    for column, spec in expected.items():
        source = spec.split(":", 1)[0]
        assert SENTINELS[source] in str(contact[column]), (plugin, column)


def test_arrl_ss_parses_the_received_exchange():
    contact = _run(
        "arrl_ss_cw",
        {
            "SNTText": "599",
            "RCVText": "599",
            "SntNrText": "12",
            "Exchange1Text": "12 A 78 CT",
        },
    )
    assert contact["SentNr"] == "12"
    assert contact["NR"] == "12"
    assert contact["Prec"] == "A"
    assert contact["CK"] == "78"
    assert contact["Sect"] == "CT"
