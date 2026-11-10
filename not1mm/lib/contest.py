"""The base class every contest plugin is built on.

A contest plugin used to be a *module* of functions whose first argument was
the main window -- ``points(self)``, ``cabrillo(self, encoding)`` and so on,
with the same two hundred lines of Cabrillo boilerplate copied into every one
of them.  A contest is now a ``class Contest(ContestBase)`` that declares only
what is different about that contest; everything else lives here, so the class
is as short as the difference really is.

Attribute names follow the N1MM User Defined Contest (UDC) file format where
the concept exists there:
https://n1mmwp.hamdocs.com/appendices/udc-editor/
so that a .udc file can later be turned into the same kind of object without
inventing a second vocabulary for the same things.  Knobs with no UDC
equivalent (``advance_on_space``, the ESM hooks) keep plain names.

Three names, three jobs:

* ``DisplayName`` is what the application shows: the contest picker and the
  window title.
* ``CabrilloName`` is the sponsor's name for the contest, and so the Cabrillo
  ``CONTEST:`` value, the base of the log filenames, the identifier kept in the
  database (``ContestInstance.ContestName``) and the directory the contest's
  macro files live in (``~/.local/share/not1mm/<identifier>``).  See
  :func:`contest_id`.
* ``ContestName`` overrides the identifier, for the few contests that share a
  Cabrillo name with another but are not interchangeable.

The old spellings -- ``name``, ``cabrillo_name``, ``mode``, ``dupe_type``,
``columns`` -- are still readable through the aliases below, so nothing in the
application had to change at the same time.

A plugin's class is instantiated once with the main window::

    self.contest = load_contest(name, self)
    self.contest.init_contest()

and reaches the window through ``self.parent``.
"""

from __future__ import annotations

import functools
import importlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib import plugin_common
from not1mm.lib import version
from not1mm.lib.plugin_common import gen_adif, get_points

logger = logging.getLogger(__name__)

# Where contests are defined.
PACKAGE_PATH = Path(__file__).resolve().parent.parent
PLUGIN_PATH = PACKAGE_PATH / "plugins"

# The five entry-window widgets a TAB cycle can visit.
ENTRY_FIELDS = ("callsign", "sent", "receive", "other_1", "other_2")

# The four entry fields that can be shown or hidden.
ENTRY_WIDGETS = ("field1", "field2", "field3", "field4")

# The log window columns almost every contest starts from.
LOG_INFO = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "PTS",
]


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Write one Cabrillo line, re-encoded through *file_encoding*.

    A bare ``print`` to the file would fail on operators whose name is not
    ASCII in the chosen encoding; this drops what cannot be encoded instead of
    dying half way through the log.
    """
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def contest_id(contest) -> str | None:
    """The identifier of *contest*: its Cabrillo name unless it overrides it.

    The Cabrillo name is what the sponsor's log checker recognises, so it is
    what identifies the contest everywhere technical: the database column, the
    log filenames, the directory under ``~/.local/share/not1mm``.  A contest
    that shares its Cabrillo name with another but is not interchangeable --
    or that has no meaningful one -- sets ``ContestName`` and is identified by
    that instead.  (N1MM's UDC files call this field ``Name``.)

    Works on anything carrying the metadata: an instance, a class or a module.
    """
    for attribute in ("ContestName", "CabrilloName", "cabrillo_name"):
        value = getattr(contest, attribute, None)
        if isinstance(value, str) and value:
            return value
    return None


def path_name(identifier: str) -> str:
    """*identifier* as a file or directory name.

    A Cabrillo name can contain a space ("FD CW") or not be upper case at all
    ("Schwaben Contest"); a log file or directory called that is asking for
    trouble, so the spaces become underscores.  The log itself keeps the name
    as it is.
    """
    return identifier.replace(" ", "_")


class ContestBase:
    """Common behaviour of a contest plugin.

    Subclasses set the attributes below and override the handful of methods
    that are genuinely contest-specific: :meth:`points`,
    :meth:`set_contact_vars`, :meth:`cabrillo_qso_line`, and the multiplier
    methods when the contest has multipliers.
    """

    # -- identity (UDC [Contest] names) -------------------------------------
    DisplayName = None  # "CQ WPX CW"; shown, and used as a directory name
    CabrilloName = None  # "CQ-WPX-CW"; the Cabrillo CONTEST: value
    # The identifier, where it is not simply the Cabrillo name.  Only the few
    # contests that share a Cabrillo name but are not interchangeable set this
    # -- see contest_id().  N1MM's UDC files call the field Name.
    ContestName = None
    EXCHANGE_HINT = ""  # placeholder in the New Contest dialog
    SOAPBOX_HINT = ""
    Mode = "BOTH"  # CW SSB BOTH RTTY
    DupeType = 2  # 1 contest, 2 band, 3 band+mode, 4 none, 5 plugin decides
    ADIFContestID = ""  # CONTEST_ID written into exported ADIF

    # -- entry window -------------------------------------------------------
    # These defaults describe the exchange by far the most common in contests:
    # RST sent, a serial number, RST received.  A contest that sends a name, a
    # grid, a section or a province sets them (or overrides interface()).
    #
    # Which of the four entry fields this contest uses ...
    EntryFields = ENTRY_WIDGETS
    # ... and what they are called.  FrameText is (sent, other, exchange);
    # an empty string leaves that label alone.
    FrameText = ("SNT", "SentNR", "RcvNR")
    # Screen-reader names, one per entry field; an empty string is skipped.
    AccessibleNames = ("RST Sent", "", "Sent Number", "Received Number")
    # The order TAB walks the entry fields in.  Shift-TAB walks the same
    # order backwards unless a contest overrides TabOrderPrev.
    TabOrder = ENTRY_FIELDS
    TabOrderPrev = None

    # not1mm-specific: whether other_1/other_2 have their spaces stripped as
    # they are typed.  Deliberately *not* given a default here -- the absence
    # of this attribute means "do not touch the spaces", which the ten-metre
    # contests rely on ("Name 1010# SPC" and friends have significant spaces).
    # Contests that had it declare it.

    # -- log window ---------------------------------------------------------
    LogInfo = list(LOG_INFO)

    # -- capabilities (the old hasattr() probes) ---------------------------
    UsesESM = True  # process_esm() drives the ESM state machine
    SupportsFT8 = False  # ft8_handler() accepts WSJT-X/FlDigi packets
    WritesEDI = False  # edi() writes a VHF/UHF EDI file
    SendsRTCScore = False  # online_score_xml() feeds the real-time score page

    def __init__(self, parent):
        self.parent = parent  # the main window (or the contest harness)

    # -- the names the application used before this was a class -------------
    @property
    def name(self):
        """The old name for :attr:`DisplayName`."""
        return self.DisplayName

    @property
    def cabrillo_name(self):
        """The old name for :attr:`CabrilloName`."""
        return self.CabrilloName

    @property
    def mode(self):
        """The old name for :attr:`Mode`."""
        return self.Mode

    @property
    def dupe_type(self):
        """The old name for :attr:`DupeType`."""
        return self.DupeType

    @property
    def columns(self):
        """The old name for :attr:`LogInfo`."""
        return self.LogInfo

    # -- setup --------------------------------------------------------------
    def init_contest(self):
        """Set up the entry window and the TAB order for this contest."""
        self.set_tab_next()
        self.set_tab_prev()
        self.interface()
        self.parent.next_field = self.parent.other_2

    def interface(self):
        """Show the entry fields this contest uses and label them."""
        parent = self.parent
        for field in ENTRY_WIDGETS:
            widget = getattr(parent, field)
            if field in self.EntryFields:
                widget.show()
            else:
                widget.hide()
        for label, text in zip(
            ("snt_label", "other_label", "exch_label"), self.FrameText
        ):
            if text:
                getattr(parent, label).setText(
                    QtWidgets.QApplication.translate("ContestPlugin", text)
                )
        # The accessible name goes on the line edit, not on the frame: the
        # frame is only the show/hide container, and the line edit is the
        # widget that takes focus, so it is the one a screen reader names.
        for field, accessible in zip(ENTRY_FIELDS[1:], self.AccessibleNames):
            if accessible:
                getattr(parent, field).setAccessibleName(accessible)

    def set_tab_next(self):
        """TAB walks the entry fields in :attr:`TabOrder`, then wraps.

        A field the order leaves out -- a hidden one, or an RST field the
        contest skips -- advances to the next field the order does visit, in
        the window's own order.  TAB moves forward, so it does not wrap to the
        first field unless there is nothing after it.
        """
        parent = self.parent
        fields = [getattr(parent, name) for name in self.TabOrder]
        following = {}
        for index, field in enumerate(fields):
            following[field] = fields[(index + 1) % len(fields)]
        visited = set(self.TabOrder)
        for index, name in enumerate(ENTRY_FIELDS):
            widget = getattr(parent, name)
            if widget in following:
                continue
            after = [n for n in ENTRY_FIELDS[index + 1 :] if n in visited]
            following[widget] = getattr(parent, after[0]) if after else fields[0]
        parent.tab_next = following

    def set_tab_prev(self):
        """Shift-TAB walks :attr:`TabOrderPrev` backwards.

        By default that is :attr:`TabOrder` itself, i.e. the reverse cycle of
        :meth:`set_tab_next`.  A contest whose fields collapse onto each other
        (several fields all advancing to the same one) can set TabOrderPrev to
        get its own order back.  A field the order leaves out goes back to the
        previous field the order visits, in the window's own order.
        """
        parent = self.parent
        order = self.TabOrder if self.TabOrderPrev is None else self.TabOrderPrev
        fields = [getattr(parent, name) for name in order]
        previous = {}
        for index, field in enumerate(fields):
            previous[field] = fields[index - 1]
        visited = set(order)
        for index, name in enumerate(ENTRY_FIELDS):
            widget = getattr(parent, name)
            if widget in previous:
                continue
            before = [n for n in ENTRY_FIELDS[:index] if n in visited]
            previous[widget] = getattr(parent, before[-1]) if before else fields[-1]
        parent.tab_prev = previous

    # -- logging ------------------------------------------------------------
    def reset_label(self):
        """Called after a field is cleared.  Only a few contests need this."""

    def predupe(self):
        """Called once the callsign has been entered.  Most contests don't."""

    def prefill(self):
        """Fill in the sent serial number, unless the operator typed one.

        This is the serial-number default; a contest whose sent exchange is a
        name, a grid or a province overrides it.
        """
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def points(self):
        """Points for the contact being logged.  Every real contest scores."""
        return 0

    def set_contact_vars(self):
        """Copy the entry fields into ``self.parent.contact``."""

    # -- the score display --------------------------------------------------
    def show_qso(self):
        """Number of QSOs in the log."""
        result = self.parent.database.fetch_qso_count()
        if result:
            return int(result.get("qsos", 0))
        return 0

    def show_mults(self):
        """Multiplier count for the score display; 0 when there are none."""
        return 0

    def calc_score(self):
        """Claimed score before multipliers, which most contests apply."""
        result = self.parent.database.fetch_points()
        if result is not None:
            score = result.get("Points", "0")
            if score is None:
                score = "0"
            return int(score)
        return 0

    def recalculate_mults(self):
        """Recompute per-contact multipliers after the log changed.

        Only contests that mark multipliers on the contact need this.
        """

    # -- the score page / cluster -------------------------------------------
    def get_mults(self):
        """Multipliers for the real-time score XML."""
        return {}

    def just_points(self):
        """Raw points before multipliers, for the real-time score XML."""
        return get_points(self.parent)

    def online_score_xml(self):
        """The XML the real-time score page wants.

        Set :attr:`SendsRTCScore` for the contests that used to import this
        from :mod:`not1mm.lib.plugin_common`; the application asks for it by
        that flag, not by looking for the method.
        """
        return plugin_common.online_score_xml(self.parent)

    # -- the FT8/digital handler -------------------------------------------
    def set_self(self):
        """Hand the main window to the plugin.  The base already has it."""

    # -- export -------------------------------------------------------------
    def adif(self):
        """Export the log as ADIF."""
        gen_adif(self.parent, self.CabrilloName, self.ADIFContestID)

    def cabrillo(self, filename, file_encoding):
        """Write the Cabrillo file, one :meth:`cabrillo_qso_line` per QSO.

        The file to write is the caller's business: the export asks for it with
        a save dialog and hands the answer here, see
        :func:`not1mm.lib.plugin_common.generate_cabrillo`.
        """
        parent = self.parent
        logger.debug("******Cabrillo*****")
        logger.debug("Station: %s", f"{parent.station}")
        logger.debug("Contest: %s", f"{parent.contest_settings}")
        logger.debug("%s", filename)
        log = parent.database.fetch_all_contacts_asc()
        try:
            with open(filename, "w", encoding=file_encoding, newline="") as file_descriptor:
                self._cabrillo_header(file_descriptor, file_encoding)
                for contact in log:
                    output_cabrillo_line(
                        self.cabrillo_qso_line(contact),
                        "\r\n",
                        file_descriptor,
                        file_encoding,
                    )
                output_cabrillo_line(
                    "END-OF-LOG:", "\r\n", file_descriptor, file_encoding
                )
            parent.show_message_box(f"Cabrillo saved to: {filename}")
        except IOError as exception:
            logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
            parent.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
            return

    def _cabrillo_header(self, file_descriptor, file_encoding):
        """Write everything before the first QSO line.

        The station and category lines are the same for every contest; only
        the handful of contests that omit or reorder them write their own
        :meth:`cabrillo`.
        """
        parent = self.parent
        station = parent.station
        settings = parent.contest_settings

        def line(text):
            output_cabrillo_line(text, "\r\n", file_descriptor, file_encoding)

        line("START-OF-LOG: 3.0")
        line(f"CREATED-BY: Not1MM v{version.__version__}")
        line(f"CONTEST: {self.CabrilloName}")
        if station.get("Club", ""):
            line(f"CLUB: {station.get('Club', '').upper()}")
        line(f"CALLSIGN: {station.get('Call', '')}")
        line(f"LOCATION: {station.get('ARRLSection', '')}")
        line(f"CATEGORY-OPERATOR: {settings.get('OperatorCategory', '')}")
        line(f"CATEGORY-ASSISTED: {settings.get('AssistedCategory', '')}")
        line(f"CATEGORY-BAND: {settings.get('BandCategory', '')}")
        mode = settings.get("ModeCategory", "")
        if mode in ("SSB+CW", "SSB+CW+DIGITAL"):
            mode = "MIXED"
        line(f"CATEGORY-MODE: {mode}")
        line(f"CATEGORY-TRANSMITTER: {settings.get('TransmitterCategory', '')}")
        if settings.get("OverlayCategory", "") != "N/A":
            line(f"CATEGORY-OVERLAY: {settings.get('OverlayCategory', '')}")
        line(f"GRID-LOCATOR: {station.get('GridSquare', '')}")
        line(f"CATEGORY-POWER: {settings.get('PowerCategory', '')}")
        line(f"CLAIMED-SCORE: {self.calc_score()}")
        ops = ""
        for op in parent.database.get_ops():
            ops += f"{op.get('Operator', '')}, "
        if station.get("Call", "") not in ops:
            ops += f"@{station.get('Call', '')}"
        else:
            ops = ops.rstrip(", ")
        line(f"OPERATORS: {ops}")
        line(f"NAME: {station.get('Name', '')}")
        line(f"ADDRESS: {station.get('Street1', '')}")
        line(f"ADDRESS-CITY: {station.get('City', '')}")
        line(f"ADDRESS-STATE-PROVINCE: {station.get('State', '')}")
        line(f"ADDRESS-POSTALCODE: {station.get('Zip', '')}")
        line(f"ADDRESS-COUNTRY: {station.get('Country', '')}")
        line(f"EMAIL: {station.get('Email', '')}")

    def cabrillo_mode(self, mode: str) -> str:
        """The Cabrillo mode code for an ADIF mode.

        Cabrillo knows five -- CW, PH, FM, RY and DG
        (https://wwrof.org/cabrillo/cabrillo-qso-data/) -- so RTTY is written
        ``RY`` and never ``RTTY``.  The PSK sub-codes are a sponsor's, not
        Cabrillo's: the Russian WW PSK Contest asks for BPSK31/BPSK63/BPSK125
        as ``PS``/``PM``/``PO``
        (https://www.rdrclub.ru/index.php/russian-ww-psk-contest/49-rus-ww-psk-rules).
        RSGB counts them differently -- PSK63 is ``PS`` there
        (https://www.rsgbcc.org/hf/rules/2025/rautumn.shtml) -- so a contest
        that follows another sponsor overrides this method.
        """
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB"):
            return "PH"
        if mode == "RTTY":
            return "RY"
        if mode in ("PSK31", "BPSK31"):
            return "PS"
        if mode in ("PSK63", "BPSK63"):
            return "PM"
        if mode in ("PSK125", "BPSK125"):
            return "PO"
        return mode

    def cabrillo_qso_line(self, contact):
        """One ``QSO:`` line of the Cabrillo file.

        The default is the exchange layout almost every contest uses: RST and
        a serial number, sent and received.  A contest that sends a name, a
        grid, a section or something else overrides this.
        """
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
        )

    # -- ESM ----------------------------------------------------------------
    def process_esm(self, new_focused_widget=None, with_enter=False):
        """Drive the Enter-Sends-Message state machine for this contact.

        Which widget counts as "the exchange" differs between contests; so
        does the way the macros get sent.  Both are handled by overriding
        this, as the RTTY contests do.
        """
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
            parent.F1,
            parent.F2,
            parent.F3,
            parent.F4,
            parent.F5,
            parent.F6,
            parent.F7,
            parent.F8,
            parent.F9,
            parent.F10,
            parent.F11,
            parent.F12,
        ):
            parent.restore_button_color(a_button)

        buttons_to_send = []
        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_2.text().isnumeric():
                    # If the operator corrected a busted callsign after the
                    # exchange was already sent, resend the corrected call
                    # ahead of the QRZ/TU macro so the other station logs the
                    # right callsign before the QSO is wiped.
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_2.text().isnumeric():
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

    def _resend_corrected_call(self, buttons_to_send):
        """Queue HISCALL again when the callsign was fixed after the exchange."""
        parent = self.parent
        if (
            parent.pref.get("esm_send_corrected_call")
            and parent.esm_call_sent
            and parent.callsign.text() != parent.esm_call_sent
        ):
            parent.make_button_green(parent.esm_dict["HISCALL"])
            buttons_to_send.append(parent.esm_dict["HISCALL"])


class _LegacyContest:
    """Adapts an unconverted plugin *module* to the class-style API.

    The plugins that have not been converted yet are still modules of
    functions whose first argument is the main window.  Everything here exists
    so the application can treat every contest the same way while the plugins
    are converted one family at a time; it goes away with the last module.

    The capability flags are computed from the module, so the application
    never has to know which kind of contest it is holding.
    """

    def __init__(self, module, parent):
        self._module = module
        self.parent = parent

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        value = getattr(self._module, name)
        if callable(value):
            # The old functions want the main window as their `self`.
            return functools.partial(value, self.parent)
        return value

    @property
    def UsesESM(self):
        return hasattr(self._module, "process_esm")

    @property
    def SupportsFT8(self):
        return hasattr(self._module, "ft8_handler")

    @property
    def WritesEDI(self):
        return hasattr(self._module, "edi")

    @property
    def SendsRTCScore(self):
        return hasattr(self._module, "online_score_xml")


def _import_optional(dotted_name: str):
    """Import *dotted_name*, or None if there is no such module.

    A ModuleNotFoundError raised from *inside* a module is not swallowed --
    only the lookup of the module itself counts.
    """
    try:
        return importlib.import_module(dotted_name)
    except ModuleNotFoundError as exc:
        if exc.name != dotted_name:
            raise
        return None


def _import_source(source: str):
    """The module a contest is defined in, by the name of its file.

    A contest is ``not1mm/plugins/<source>.py``, whether it is still a module
    of functions or already a class; ``<source>`` is what the identifiers in
    the database used to be.
    """
    return _import_optional(f"not1mm.plugins.{source}")


# An identifier that could be a file or directory name; anything with a dot or
# a space in it (most Cabrillo names) is not worth trying to import.
_SOURCE_NAME = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class ContestInfo:
    """One contest this installation can open."""

    source: str  # where it is defined, e.g. "cq_wpx_cw"
    identifier: str  # what the database stores, e.g. "CQ-WPX-CW"
    display_name: str  # what to show, e.g. "CQ WPX CW"


_AVAILABLE: list[ContestInfo] | None = None


def available_contests() -> list[ContestInfo]:
    """Every contest that ships with not1mm.

    Built on demand, because it has to import each definition to read what it
    declares -- cheap once, and only needed when a contest has to be found by
    something other than the name of the file it lives in.
    """
    global _AVAILABLE
    if _AVAILABLE is not None:
        return _AVAILABLE
    found = []
    for source in _contest_sources():
        module = _import_source(source)
        if module is None:
            continue
        metadata = getattr(module, "Contest", None) or module
        identifier = contest_id(metadata)
        if identifier is None:
            logger.warning("Contest %s declares no Cabrillo name", source)
            continue
        found.append(
            ContestInfo(
                source=source,
                identifier=identifier,
                display_name=getattr(metadata, "DisplayName", None)
                or getattr(metadata, "name", "")
                or "",
            )
        )
    _AVAILABLE = found
    return found


def _contest_sources() -> list[str]:
    """The name of every contest definition that ships with not1mm."""
    return sorted(
        path.stem for path in PLUGIN_PATH.glob("*.py") if path.stem != "__init__"
    )


def _find_module(identifier: str):
    """The module for *identifier*.

    Whatever the database recorded over the years has to keep loading: the id
    (the Cabrillo name), the name of the file the contest lives in, or its
    display name.  A source name is tried first because that is a plain import;
    the Cabrillo name needs the whole tree scanned to see which file declares
    it.
    """
    if not isinstance(identifier, str) or not identifier:
        return None
    if _SOURCE_NAME.fullmatch(identifier):
        module = _import_source(identifier)
        if module is not None:
            return module

    wanted = identifier.casefold()
    matches = [
        info
        for info in available_contests()
        if wanted
        in (
            info.identifier.casefold(),
            info.source.casefold(),
            info.display_name.casefold(),
        )
    ]
    if len(matches) > 1:
        # Two definitions share an identifier and it does not say which one is
        # meant -- the fall and spring Ten-Ten QSO parties, for one.  Say so
        # rather than pick silently.
        logger.warning(
            "Contest %r is ambiguous, using %s: %s",
            identifier,
            matches[0].source,
            ", ".join(info.source for info in matches),
        )
    return _import_source(matches[0].source) if matches else None


def load_contest(identifier: str, parent):
    """Import the contest called *identifier* and bind it to the main window.

    A converted contest is a ``class Contest(ContestBase)``; an unconverted one
    is still a module of functions.  Both live in ``not1mm.plugins.<source>``,
    and the test fixtures for either are in ``not1mm/contest/<source>/``.
    """
    module = _find_module(identifier)
    if module is None:
        raise ModuleNotFoundError(f"no contest plugin named {identifier!r}")
    contest_class = getattr(module, "Contest", None)
    if contest_class is None:
        return _LegacyContest(module, parent)
    return contest_class(parent)


def contest_metadata(identifier: str):
    """Whatever carries the metadata for *identifier*.

    The ``Contest`` class for a converted contest, the module for an
    unconverted one, None when there is no such contest.
    """
    module = _find_module(identifier)
    if module is None:
        return None
    return getattr(module, "Contest", None) or module


def contest_identifier_for_display(display_name: str) -> str | None:
    """The identifier of the contest the picker shows as *display_name*.

    The picker's entries are not the contests' own display names -- they are
    their own short labels ("OK1WC", "LZ-DX", "10 10 FALL CW"), and what links
    them to a contest is the fold the application has always applied: lower
    case, spaces to underscores, which lands on the name of the file the
    contest lives in.  That fold also happens to be what older databases
    stored, so it has to keep resolving.  A contest's own display name is
    accepted too, for callers that have one.
    """
    folded = display_name.casefold().replace(" ", "_")
    wanted = display_name.casefold()
    available = available_contests()
    for info in available:
        if info.source.casefold() == folded:
            return info.identifier
    for info in available:
        if info.display_name.casefold() == wanted:
            return info.identifier
    return None

