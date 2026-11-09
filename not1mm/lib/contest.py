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
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib import plugin_common
from not1mm.lib import version
from not1mm.lib.plugin_common import gen_adif, get_points

logger = logging.getLogger(__name__)

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


def _find_module(name: str):
    """The module for contest *name*.

    A contest is ``not1mm/plugins/<name>.py``, whether it is a class already or
    still a module of functions.  The test fixtures live in
    ``not1mm/contest/<name>/``, which is not importable, so there is nothing
    here to tell apart.
    """
    return _import_optional(f"not1mm.plugins.{name}")


def load_contest(name: str, parent):
    """Import contest *name* and bind it to the main window.

    A converted contest is a ``class Contest(ContestBase)``; an unconverted one
    is still a module of functions.  Both live in ``not1mm/plugins/<name>.py``.
    """
    module = _find_module(name)
    if module is None:
        raise ModuleNotFoundError(f"no contest plugin named {name!r}")
    contest_class = getattr(module, "Contest", None)
    if contest_class is None:
        return _LegacyContest(module, parent)
    return contest_class(parent)


def contest_metadata(name: str):
    """Whatever carries the metadata for *name*.

    The ``Contest`` class for a converted contest, the module for an
    unconverted one, None when there is no such contest.
    """
    module = _find_module(name)
    if module is None:
        return None
    return getattr(module, "Contest", None) or module
