"""ARRL Field Day plugin

Find rules at: http://www.arrl.org/field-day

160-10m, once per band and mode.  The exchange is the class (``1D``, ``2A``, ...)
and the ARRL/RAC section; phone is 1 point and CW or digital 2 (rule 7.1), and
the score is the points times the number of band/mode combinations worked.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM", "PH")


class Contest(ContestBase):
    """ARRL Field Day."""

    DisplayName = "ARRL Field Day"
    CabrilloName = "ARRL-FD"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "1D ORG"
    SupportsFT8 = True
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # Only the class and section fields are used; the RSTs are hidden.
    EntryFields = ("field3", "field4")
    FrameText = ("", "Class", "Section")
    AccessibleNames = ("", "", "Class", "Section")
    # The module focused the class field after a lookup, not the section.
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Exchange1",
        "Sect",
        "PTS",
        "Operator",
    ]
    # The score is the points times the number of band/mode combinations worked,
    # not a keyed multiplier, so show_mults() is that count and get_mults() is
    # empty (as the module's was).
    NumMults = 1
    Multiplier1Name = "Grid"
    MultSqlString = "Grid"
    IsMult1Per = 4

    def points(self):
        """1 point phone, 2 CW or digital (rule 7.1)."""
        if self.parent.contact_is_dupe > 0:
            return 0
        mode = str(self.parent.contact.get("Mode", "")).upper()
        if not mode:
            return 0
        if mode in _PHONE_MODES:
            return 1
        return 2

    def show_mults(self):
        """The number of band/mode combinations worked."""
        result = self.parent.database.get_unique_band_and_mode()
        return int(result.get("mult", 0)) if result else 0

    def get_mults(self):
        """The score page is told nothing, as the module told it."""
        return {}

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1`` (see §29)."""

    def set_contact_vars(self):
        """The exchange; the class and section are the received ones."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = parent.other_1.text().upper()
        parent.contact["Sect"] = parent.other_2.text().upper()

    def prefill(self):
        """Nothing to prefill: other_1 is the class, not the sent serial."""

    def cabrillo_qso_line(self, contact):
        """The Field Day line: the operator's own exchange, then class/section.

        The base's line sends a serial; here the sent exchange is the class and
        section from the setup, and the received one is the class and section.
        """
        parent = self.parent
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        sent = parent.contest_settings.get("SentExchange", "").ljust(9).upper()
        return (
            f"QSO: {frequency} {self._fd_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{sent}"
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Exchange1', '')).ljust(3)} "
            f"{str(contact.get('Sect', '')).ljust(6)}"
        )

    def _fd_mode(self, mode):
        """The Cabrillo mode code: CW, PH or DG."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "FM"):
            return "PH"
        if mode in ("FT8", "FT4", "RTTY"):
            return "DG"
        return mode

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The exchange is the class *and* the section, so both fields have to be
        filled before the contact is finished.
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

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")

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

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = packet.get("CLASS", "ERR")
        parent.contact["Sect"] = packet.get("ARRL_SECT", "ERR")
        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.other_1.setText(packet.get("CLASS", "ERR"))
        parent.other_2.setText(packet.get("ARRL_SECT", "ERR"))
        parent.save_contact()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('Sect', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the class and section from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Exch1', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
