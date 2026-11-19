"""UDC's QsoErrorString drives ESM's "is the exchange there?" decision.

The two-box contests used to carry a copy of ``process_esm`` whose only change
from the base was "both extra boxes must be filled".  They now declare
``QsoErrorString`` and use the base machine; these tests pin the parser, the
readiness hook, and the replacement itself.
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from not1mm.lib.contest import load_contest, parse_qso_error_string
from not1mm.lib.contest import PLUGIN_PATH

TWO_BOX = [
    "canada_day",
    "darc_schwaben",
    "darc_vhf",
    "darc_xmas",
    "hadx",
    "nac_vhf",
    "pacc",
    "rda_contest",
    "rdxc",
    "spdx",
    "wag",
]
TWO_BOX_RULE = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"


# -- the parser -------------------------------------------------------------


def test_undeclared_keeps_the_single_exchange_check():
    rules = parse_qso_error_string(None, "RcvNrText")
    assert [(r.box, r.kind, r.allow_empty) for r in rules] == [
        ("RcvNrText", "any", False)
    ]


def test_empty_string_means_no_checks():
    assert parse_qso_error_string("", "RcvNrText") == ()


def test_box_and_rule_use_an_underscore():
    (rule,) = parse_qso_error_string("SntNrText_Any_not_Empty", "RcvNrText")
    assert rule.box == "SntNrText"
    assert rule.kind == "any"
    assert not rule.allow_empty


def test_two_specs_are_comma_separated():
    first, second = parse_qso_error_string(TWO_BOX_RULE, "RcvNrText")
    assert (first.box, second.box) == ("SntNrText", "RcvNrText")
    assert not first.allow_empty and not second.allow_empty


def test_a_bare_rule_applies_to_the_exchange_field():
    (rule,) = parse_qso_error_string("Any_not_Empty", "Exchange1Text")
    assert rule.box == "Exchange1Text"


def test_any_allows_empty_but_not_empty_does_not():
    (any_rule,) = parse_qso_error_string("MiscText_Any", "Exchange1Text")
    (required,) = parse_qso_error_string("MiscText_Any_not_Empty", "Exchange1Text")
    assert any_rule.accepts("")
    assert not required.accepts("")


def test_numeric_and_grid_shapes():
    (numeric,) = parse_qso_error_string("Exchange1Text_Numeric_not_Empty", "x")
    (grid,) = parse_qso_error_string("GridSquareText_Grid", "x")
    assert numeric.accepts("001")
    assert not numeric.accepts("1A")
    assert grid.accepts("JO89")
    assert grid.accepts("JO89ab")
    assert not grid.accepts("JO8")


def test_an_unknown_rule_is_an_error():
    with pytest.raises(ValueError, match="unknown rule"):
        parse_qso_error_string("RcvNrText_Anything", "RcvNrText")


# -- readiness --------------------------------------------------------------


class FakeEdit:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):  # noqa: N802
        self._text = text

    def setStyleSheet(self, style):  # noqa: N802
        ...

    def toolTip(self):
        return self._text

    def __bool__(self):
        return True


class FakeFields:
    def __init__(self, boxes, callsign="K1ABC"):
        self._edits = {name: FakeEdit() for name in boxes}
        self.callsign = FakeEdit(callsign)

    def edit(self, name):
        if name in ("callsign", "CallSignText"):
            return self.callsign
        return self._edits.get(name)

    def __iter__(self):
        for name, edit in self._edits.items():
            yield SimpleNamespace(name=name, edit=edit, spec=SimpleNamespace(column=""))


class FakeWindow:
    """Only what the base process_esm touches."""

    def __init__(self, fields):
        self.fields = fields
        self.callsign = fields.callsign
        self.pref = {"run_state": True, "esm_send_corrected_call": False}
        self.esm_dict = {
            name: FakeEdit(name)
            for name in ("CQ", "HISCALL", "EXCH", "AGN", "QRZ", "MYCALL", "QSOB4")
        }
        for index in range(1, 13):
            setattr(self, f"F{index}", FakeEdit(f"F{index}"))
        self.contact = {"Continent": "NA"}
        self.contact_is_dupe = 0
        self.current_widget_object = None
        self.inputs_dict = {}
        self.esm_call_sent = ""
        self.saved = 0
        self.sent_buttons = []

    def restore_button_color(self, button): ...

    def make_button_green(self, button): ...

    def process_function_key(self, button):
        self.sent_buttons.append(button)

    def save_contact(self):
        self.saved += 1


def _window_for(plugin):
    contest = load_contest(plugin, None)
    boxes = [box.spec.name for box in contest.entry_boxes()]
    window = FakeWindow(FakeFields(boxes))
    contest.parent = window
    return contest, window


@pytest.mark.parametrize("plugin", TWO_BOX)
def test_the_two_box_contests_have_no_esm_override(plugin):
    cls = importlib.import_module(f"not1mm.plugins.{plugin}").Contest
    assert cls.QsoErrorString == TWO_BOX_RULE
    assert "process_esm" not in cls.__dict__


@pytest.mark.parametrize("plugin", TWO_BOX)
def test_the_rules_name_declared_boxes(plugin):
    contest = load_contest(plugin, None)
    declared = {box.spec.name for box in contest.entry_boxes()}
    assert {rule.box for rule in contest.qso_error_rules()} <= declared


def test_every_declared_qso_error_string_names_declared_boxes():
    for path in sorted(PLUGIN_PATH.glob("*.py")):
        if path.stem in {"__init__", "base"}:
            continue
        module = importlib.import_module(f"not1mm.plugins.{path.stem}")
        if getattr(module.Contest, "QsoErrorString", None) in (None, ""):
            continue
        contest = load_contest(path.stem, None)
        declared = {box.spec.name for box in contest.entry_boxes()}
        rules = contest.qso_error_rules()
        assert rules, path.stem
        assert {rule.box for rule in rules} <= declared, path.stem


ADOPTED_TWO_BOX = [
    "arrl_field_day",
    "winter_field_day",
    "cwo",
    "cwt",
    "k1usn_sst",
    "phone_weekly_test",
    "raem",
]


@pytest.mark.parametrize("plugin", ADOPTED_TWO_BOX)
def test_the_two_box_family_has_no_esm_override(plugin):
    cls = importlib.import_module(f"not1mm.plugins.{plugin}").Contest
    assert cls.QsoErrorString
    assert "process_esm" not in cls.__dict__


@pytest.mark.parametrize("plugin", ADOPTED_TWO_BOX)
def test_each_two_box_rule_gates_the_contact(plugin):
    contest, window = _window_for(plugin)
    rules = contest.qso_error_rules()
    assert len(rules) == 2
    edits = [window.fields.edit(rule.box) for rule in rules]
    assert all(edit is not None for edit in edits)

    for missing in edits:
        window.sent_buttons.clear()
        window.saved = 0
        for edit in edits:
            edit.setText("X")
        missing.setText("")
        contest.process_esm(new_focused_widget=edits[0], with_enter=True)
        assert window.esm_dict["AGN"] in window.sent_buttons
        assert window.saved == 0

    for edit in edits:
        edit.setText("X")
    contest.process_esm(new_focused_widget=edits[0], with_enter=True)
    assert window.saved == 1


# -- the derived field names ------------------------------------------------


@pytest.mark.parametrize(
    "plugin,expected",
    [
        ("ari_dx", ("RcvNrText", "RcvNrText")),
        ("10_10_fall_cw", ("Exchange1Text", "Exchange1Text")),
        ("naqp_cw", ("NameText", "SectText")),
        ("cq_ww_rtty", ("Exchange1Text", "SectText")),
        ("ca_qso_party", ("RcvNrText", "Exchange1Text")),
        ("arrl_ss_cw", ("Exchange1Text", "Exchange1Text")),
        ("ssa_mt_cw", ("RcvNrText", "Exchange1Text")),
        ("lz-dx", ("RcvNrText", "RcvNrText")),
        ("cq_ww_vhf", ("RcvNrText", "RcvNrText")),  # still legacy field3/field4
    ],
)
def test_next_and_esm_fields_are_derived(plugin, expected):
    contest = load_contest(plugin, None)
    assert (contest.next_field_name(), contest.esm_field_name()) == expected


def test_a_reports_only_window_still_has_a_lookup_landing():
    contest = load_contest("dxpedition", None)
    assert contest.default_next_field_name() == "RCVText"
    assert contest.default_esm_exchange_field_name() == "RCVText"


def test_migrated_contests_do_not_declare_the_two_fields():
    for path in sorted(PLUGIN_PATH.glob("*.py")):
        if path.stem in {"__init__", "base"}:
            continue
        cls = importlib.import_module(f"not1mm.plugins.{path.stem}").Contest
        if getattr(cls, "EntryWindowInfo", None) is None:
            continue
        assert cls.NextField is None, path.stem
        assert cls.ESMExchangeField is None, path.stem


# -- the base machine, on one of the migrated contests ----------------------


@pytest.mark.parametrize("plugin", ["wag", "canada_day", "nac_vhf"])
def test_one_empty_box_asks_for_a_repeat(plugin):
    contest, window = _window_for(plugin)
    window.fields.edit("SntNrText").setText("001")
    window.fields.edit("RcvNrText").setText("")
    contest.process_esm(
        new_focused_widget=window.fields.edit("SntNrText"), with_enter=True
    )
    assert window.saved == 0
    assert window.esm_dict["AGN"] in window.sent_buttons


@pytest.mark.parametrize("plugin", ["wag", "canada_day", "nac_vhf"])
def test_both_boxes_finish_the_contact_from_either(plugin):
    for box in ("SntNrText", "RcvNrText"):
        contest, window = _window_for(plugin)
        window.fields.edit("SntNrText").setText("001")
        window.fields.edit("RcvNrText").setText("JO89")
        contest.process_esm(new_focused_widget=window.fields.edit(box), with_enter=True)
        assert window.saved == 1, (plugin, box)
        assert window.esm_dict["QRZ"] in window.sent_buttons


def test_search_and_pounce_sends_the_exchange_and_logs():
    contest, window = _window_for("wag")
    window.pref["run_state"] = False
    window.fields.edit("SntNrText").setText("001")
    window.fields.edit("RcvNrText").setText("JO89")
    contest.process_esm(
        new_focused_widget=window.fields.edit("RcvNrText"), with_enter=True
    )
    assert window.sent_buttons == [window.esm_dict["EXCH"]]
    assert window.saved == 1


def test_arrl_160_is_station_dependent():
    contest, window = _window_for("arrl_160m")
    assert "process_esm" not in type(contest).__dict__
    window.contact = {"CountryPrefix": "K"}
    window.fields.edit("Exchange1Text").setText("")
    assert contest.esm_exchange_ready() is False
    window.fields.edit("Exchange1Text").setText("ORG")
    assert contest.esm_exchange_ready() is True
    window.contact = {"CountryPrefix": "DL"}
    window.fields.edit("Exchange1Text").setText("")
    assert contest.esm_exchange_ready() is True


def test_an_explicit_empty_qso_error_string_has_no_rules():
    contest, _ = _window_for("wag")
    contest.QsoErrorString = ""
    assert contest.qso_error_rules() == ()
    assert contest.esm_exchange_ready() is True
    assert contest.esm_exchange_edits()  # every non-report box is a trigger
