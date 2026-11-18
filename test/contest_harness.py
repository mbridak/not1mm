"""Shared harness for running contest plugins headlessly against a test log.

A contest plugin is a class, and it reaches the not1mm main window through
``self.parent``.  ``ContestHarness``
stands in for that main window: it owns a real on-disk
:class:`~not1mm.lib.database.DataBase`, a real cty.dat lookup, and stubs for the
handful of widgets ``imp_adif`` / ``cabrillo`` / ``edi`` touch.  With
``plugin_common.QProgressDialog`` stubbed no ``QApplication`` is needed.

The plugin lives in ``not1mm/plugins/<plugin>.py`` and its fixtures in
``not1mm/contest/<plugin>/``::

    not1mm/contest/<plugin>/<case>.adif   # input QSOs
    not1mm/contest/<plugin>/<case>.json   # station + contest settings
    not1mm/contest/<plugin>/<case>.log    # expected Cabrillo (or <case>.edi)

``<case>`` is conventionally the station callsign, so one contest can carry
several logs logged under different callsigns.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import not1mm
from not1mm.lib.contest import load_contest
from not1mm.lib.database import DataBase

# Some contests score from the *local* clock - the Remembrance Day Contest
# triples a contact logged between 0100 and 0600 local time (rule 10.5), and a
# logger can only take "local" from the machine it runs on.  Pin the tests to
# UTC so a golden log is the same wherever they run.  This is a neutral
# default, not a statement about any contest: a test that needs another zone
# has to set TZ and call tzset() itself, and put it back afterwards.
os.environ["TZ"] = "UTC"
time.tzset()

DATA_DIR = Path(not1mm.__file__).parent / "data"
CONTEST_DIR = Path(not1mm.__file__).parent / "contest"

# Deliberately synthetic.  The version is pinned so ``CREATED-BY`` in the
# golden Cabrillo files does not churn on every release bump.
VERSION_PIN = "0.0.0-test"

CTY = json.loads((DATA_DIR / "cty.json").read_text(encoding="utf-8"))


def cty_lookup(callsign: str) -> dict | None:
    """Look a callsign up in cty.dat.

    Same result as ``MainWindow.cty_lookup`` -- it returns a one-entry
    ``{matched_prefix: entry}`` dict -- but keys straight into the table instead
    of scanning all 30k entries once per prefix.
    """
    callsign = callsign.upper()
    for count in reversed(range(len(callsign))):
        searchitem = callsign[: count + 1]
        item = CTY.get(searchitem)
        if item is None:
            continue
        if item.get("exact_match"):
            if searchitem == callsign:
                return {searchitem: item}
            continue
        return {searchitem: item}
    return None


class DummyProgress:
    """Stand-in for ``QProgressDialog``: no Qt, no event loop."""

    def __init__(self, *args, **kwargs): ...

    def setWindowModality(self, *args): ...

    def setValue(self, *args): ...

    def wasCanceled(self):
        return False

    def close(self): ...


class Stub:
    """Permissive stand-in for the widgets the plugins poke at.

    Attribute access yields another callable Stub, so chains like
    ``self.field3.findChild(QLabel).setText(...)`` work, and it is falsy so
    ``if self.actionStatistics.isChecked():`` takes the else branch.
    """

    def __getattr__(self, _name):
        return lambda *args, **kwargs: Stub()

    def __bool__(self):
        return False


class FakeLineEdit:
    """Stand-in for a ``QLineEdit``."""

    def __init__(self, text: str = ""):
        self._text = text

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:  # noqa: N802
        self._text = text

    def __getattr__(self, _name):
        """Any other QLineEdit method (setAccessibleName, show, ...) is a no-op."""
        return lambda *args, **kwargs: None


def pin_versions(monkeypatch, pin: str = VERSION_PIN) -> None:
    """Freeze every version-ish global so exported logs are byte-stable.

    ``__version__`` is bound into each plugin module at import time by
    ``from not1mm.lib.version import __version__``, so patching the source
    module is not enough: every plugin module gets its own copy.
    """
    for name, module in list(sys.modules.items()):
        if not (name == "not1mm.lib.version" or name.startswith("not1mm.plugins.")):
            continue
        for attr, value in list(vars(module).items()):
            if attr.endswith("version__") and isinstance(value, str):
                monkeypatch.setattr(module, attr, pin)


# A field is ``<TAG:length>value``; an optional trailing ``:type`` is ignored.
_ADIF_FIELD = re.compile(r"<([A-Za-z0-9_]+):(\d+)(?::[A-Za-z])?>")


def validate_adif_lengths(path: Path) -> None:
    """Fail loudly on ADIF length prefixes that do not match their value.

    ``adif_io`` silently truncates a field whose declared length is too short,
    which turns an authoring typo into a bogus golden file.

    The check assumes a declared value contains no literal ``<``; that is true
    of the test logs and keeps the diagnostic exact.
    """
    text = path.read_bytes().decode("ascii", errors="replace")
    for match in _ADIF_FIELD.finditer(text):
        tag, length = match.group(1), int(match.group(2))
        value = text[match.end() : match.end() + length]
        if len(value) < length:
            raise AssertionError(f"{path.name}: <{tag}:{length}> runs past end of file")
        if "<" in value:
            raise AssertionError(
                f"{path.name}: <{tag}:{length}> is too long (swallows the next field)"
            )
        following = text[match.end() + length : match.end() + length + 1]
        if following and following not in "<>\r\n":
            raise AssertionError(
                f"{path.name}: <{tag}:{length}> is too short (next char {following!r})"
            )


def export_record_count(path: Path) -> int:
    """Number of QSO records in an exported Cabrillo (``.log``) or EDI file."""
    text = path.read_bytes().decode("utf-8", errors="replace")
    if path.suffix == ".edi":
        marker = text.find("[QSORecords;")
        body = text[marker:] if marker != -1 else ""
        return sum(1 for line in body.splitlines() if re.match(r"^\d{6};", line))
    return sum(1 for line in text.splitlines() if line.startswith("QSO: "))


@dataclass(frozen=True)
class Case:
    """One contest log fixture: an ADIF input and its expected export."""

    contest: str  # plugin module name, e.g. "euhfc"
    name: str  # case label, conventionally the station callsign
    directory: Path  # the contest directory holding <name>.adif/.json/.log

    @property
    def adif(self) -> Path:
        return self.directory / f"{self.name}.adif"

    @property
    def config(self) -> Path:
        return self.directory / f"{self.name}.json"

    def golden(self, suffix: str) -> Path:
        """Expected export: ``<name>.log`` for Cabrillo, ``<name>.edi`` for VHF."""
        return self.directory / f"{self.name}.{suffix}"

    @property
    def exports(self) -> bool:
        """Whether the plugin writes a Cabrillo/EDI log to compare against.

        A couple of plugins have no log output at all - RandomGram submits a
        list of the groups it received, not a Cabrillo - and their fixture
        carries ``"export": false`` so the runner checks their scoring only.
        """
        config = json.loads(self.config.read_text(encoding="utf-8"))
        return bool(config.get("export", True))

    @property
    def id(self) -> str:
        return f"{self.contest}/{self.name}"


def discover_cases(root: Path = CONTEST_DIR) -> list[Case]:
    """Find every ``<contest>/<case>.adif`` fixture under *root*."""
    cases: list[Case] = []
    if not root.is_dir():
        return cases
    for contest_dir in sorted(child for child in root.iterdir() if child.is_dir()):
        for adif in sorted(contest_dir.glob("*.adif")):
            cases.append(Case(contest_dir.name, adif.stem, contest_dir))
    return cases


class FakeField:
    """A Qt-free stand-in for ``not1mm.lib.fields.EntryField``."""

    def __init__(self, box, edit):
        self.box = box
        self.spec = box.spec
        self.name = box.spec.name
        self.edit = edit
        self.frame = object()
        self.label = FakeLineEdit(
            box.label if box.label is not None else box.spec.label
        )

    def set_visible(self, visible):
        self.box.visible = visible

    def set_label(self, text):
        self.label.setText(text or "")

    def set_accessible(self, name): ...

    def clear(self):
        self.edit.setText("")


# The four boxes a not-migrated plugin still describes, and where the harness
# already keeps their line edits.
_LEGACY_ATTRS = {
    "SNTText": "sent",
    "RCVText": "receive",
    "SntNrText": "other_1",
    "RcvNrText": "other_2",
}
_LEGACY_ALIASES = {
    "sent": "SNTText",
    "receive": "RCVText",
    "other_1": "SntNrText",
    "other_2": "RcvNrText",
}


class FakeFields:
    """The ``Fields`` API for a headless parent.

    It records the boxes ``ContestBase.interface()`` configures and resolves
    the old positional names onto the harness's existing line edits, so the
    shared harness keeps working without a QApplication.
    """

    def __init__(self, parent):
        self.parent = parent
        self.callsign = parent.callsign
        self._fields: dict[str, FakeField] = {}
        self._legacy = True

    def configure(self, boxes, legacy=False):
        self._legacy = legacy
        names = tuple(box.spec.name for box in boxes)
        if tuple(self._fields) != names:
            self._fields = {
                box.spec.name: FakeField(box, self._edit_for(box.spec.name))
                for box in boxes
            }
        else:
            for box in boxes:
                self._fields[box.spec.name].box = box
        return False

    def _edit_for(self, name):
        field = self._fields.get(name)
        if field is not None:
            return field.edit
        attribute = _LEGACY_ATTRS.get(name)
        if attribute is not None:
            return getattr(self.parent, attribute)
        return FakeLineEdit()

    def __iter__(self):
        return iter(self._fields.values())

    def __getattr__(self, name):
        if name == "CallSignText":
            return self.__dict__["callsign"]
        fields = self.__dict__.get("_fields", {})
        if name in fields:
            return fields[name].edit
        raise AttributeError(name)

    def field(self, name):
        return self._fields.get(name)

    def edit(self, name, default=None):
        if name in ("callsign", "CallSignText"):
            return self.callsign
        field = self._fields.get(name)
        if field is not None:
            return field.edit
        if name in _LEGACY_ALIASES:
            legacy = self.legacy_edit(name)
            return legacy if legacy is not None else default
        return default

    def names(self):
        return tuple(name for name, field in self._fields.items() if field.box.visible)

    def all_names(self):
        return tuple(self._fields)

    def display_order(self):
        return (self.callsign,) + tuple(
            field.edit for field in self._fields.values() if field.box.visible
        )

    def all_order(self):
        return (self.callsign,) + tuple(field.edit for field in self._fields.values())

    def index(self, edit):
        try:
            return self.all_order().index(edit)
        except ValueError:
            return None

    def last_field(self):
        for field in reversed(self._fields.values()):
            return field
        return None

    def last_edit(self):
        field = self.last_field()
        return field.edit if field is not None else self.callsign

    def report_edits(self):
        return tuple(
            self._fields[name].edit
            for name in ("SNTText", "RCVText")
            if name in self._fields
        )

    def by_column(self, column):
        for field in self._fields.values():
            if field.spec.column == column:
                return field
        return None

    def legacy_edit(self, name):
        if name not in _LEGACY_ALIASES:
            return None
        if self._legacy:
            field = self._fields.get(_LEGACY_ALIASES[name])
            return field.edit if field is not None else None
        extras = [
            field
            for field in self._fields.values()
            if field.spec.column not in ("SNT", "RCV")
        ]
        index = 0 if name == "other_1" else 1
        if index < len(extras):
            return extras[index].edit
        return None

    def legacy_text(self, name):
        edit = self.legacy_edit(name)
        return edit.text() if edit is not None else ""

    def inputs(self):
        if self._legacy:
            names = ("callsign", "sent", "receive", "other_1", "other_2")
        else:
            names = ("CallSignText",) + self.all_names()
        return dict(zip(self.all_order(), names))

    def clear_exchange(self):
        for name, field in self._fields.items():
            if name not in ("SNTText", "RCVText"):
                field.edit.setText("")

    def apply_font(self, *args, **kwargs): ...

    def apply_palette(self, palette): ...

    def apply_upper(self): ...


class ContestHarness:
    """Just enough of the main window to drive a plugin's import and export."""

    def __init__(self, contest_name: str, case: Case, tmp_path: Path, monkeypatch=None):
        config = json.loads(case.config.read_text(encoding="utf-8"))
        self.case = case
        self.pref = {"contest": 1, "run_state": False, **config.get("pref", {})}
        self.database = DataBase(
            str(tmp_path / "contest.db"),
            DATA_DIR,
            current_contest=self.pref["contest"],
        )
        self.station = dict(config.get("station", {}))
        self.contest_settings = dict(config.get("contest_settings", {}))
        self.ctyfile = CTY
        self.cty_lookup = cty_lookup
        self.messages: list[str] = []
        self.show_message_box = self.messages.append
        self.filepicker = lambda _kind: str(case.adif)
        self.callsign = FakeLineEdit()
        self.sent = FakeLineEdit("599")
        self.receive = FakeLineEdit("599")
        self.other_1 = FakeLineEdit()
        self.other_2 = FakeLineEdit()
        self.exch_label = FakeLineEdit()
        self.fields = FakeFields(self)
        self.after_fields_rebuilt = lambda: None
        self.contact = {}
        self.contact_is_dupe = 0
        self.dupes = 0
        self.RoverLocation = ""
        self.radio_state = {"vfoa": 0, "mode": ""}
        self.log_window = Stub()
        self.actionStatistics = Stub()
        self.statistics_window = Stub()
        self.score = Stub()
        self.mults = Stub()
        self.progress_dialog = None
        self._ready = True

        self.contest = load_contest(contest_name, self)

        # The plugin's module exists from here on, so pin the versions an
        # exported log would otherwise carry.  It has to happen after the
        # import: a plugin binds `__version__` into its own namespace with
        # `from not1mm.lib.version import __version__`, so pinning only
        # not1mm.lib.version is not enough.
        if monkeypatch is not None:
            pin_versions(monkeypatch)

        # The app runs init_contest() when a contest is loaded, and some plugins
        # park scoring state there (wag's is_german, for one).
        self.contest.init_contest()

    def __getattr__(self, name):
        """Permissive stand-in for the widgets init_contest()/interface() touch."""
        if name.startswith("_") or "_ready" not in self.__dict__:
            raise AttributeError(name)
        stub = Stub()
        object.__setattr__(self, name, stub)
        return stub

    def _is_dupe(self, contact) -> bool:
        """Mirror MainWindow.check_dupe: the contest answers the dupe question."""
        return self.contest.is_dupe(
            contact.get("Call", ""),
            contact.get("Band"),
            contact.get("Mode", ""),
        )

    def score_log(self) -> None:
        """Compute Points for every logged contact, the way live logging would.

        ``imp_adif`` maps ADIF records but only 16 of 96 plugins recompute
        ``Points`` in ``recalculate_mults``, so an imported log otherwise claims
        a score of zero.  To get the dupe decision right the log is replayed:
        each contact is checked against the database as it stood *before* it was
        logged, exactly like ``MainWindow`` does on entry, then re-inserted.
        """
        contacts = self.database.fetch_all_contacts_asc()
        self.database.exec_sql_commit(
            "delete from dxlog where ContestNR = ?;", (self.pref["contest"],)
        )
        self.dupes = 0
        for contact in contacts:
            self.contact = contact
            # the rig would be sitting on this contact's band/mode
            self.radio_state = {
                "vfoa": contact.get("Freq", 0) * 1000,
                "mode": contact.get("Mode", ""),
            }
            self.contact_is_dupe = 1 if self._is_dupe(contact) else 0
            if self.contact_is_dupe:
                self.dupes += 1
            contact["Points"] = self.contest.points()
            self.database.log_contact(contact)
        self.contest.recalculate_mults()

    def export(self, home: Path) -> Path | None:
        """Score the log, run the plugin's export, return the file written."""
        from not1mm.lib import plugin_common

        self.score_log()
        if self.contest.WritesEDI:
            plugin_common.generate_edi(self)
            produced = sorted(home.glob("*.edi"))
        else:
            plugin_common.generate_cabrillo(self, "utf-8")
            produced = sorted(home.glob("*.log"))
        return produced[-1] if produced else None
