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
from not1mm.lib.contest import load_contest

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

    def text(self):
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

    def __getattr__(self, name):
        try:
            return self._edits[name]
        except KeyError:
            raise AttributeError(name) from None

    def __iter__(self):
        return iter(self._edits.items())


class FakeDatabase:
    def mult_key_exists(self, *args, **kwargs):
        return {"count": 0}

    def fetch_all_contacts_asc(self):
        return []


def _run(plugin, values, mode="CW", station=None):
    """Load *plugin* with the boxes in *values* filled, then log the contact."""
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
        station=station or {"Call": "K6GTE"},
        current_mode=mode,
        current_sn="1",
        contest_settings={"SentExchange": "03"},
        database=FakeDatabase(),
        cty_lookup=cty_lookup,
        show_message_box=lambda *_args, **_kwargs: None,
    )
    contest.parent = parent
    contest.set_contact_vars()
    return parent.contact


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
