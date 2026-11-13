"""Winter Field Day plugin

Find rules at: https://winterfieldday.org/downloads/2026-rules-v3.pdf

160-10m, once per band and mode.  The exchange is the class (``1O``, ``2A``,
...) and the ARRL/RAC section; phone is 1 point and CW or digital 2 (FT4 and
FT8 do not count), and the score is the points times the number of band/mode
combinations worked, doubled for a QRP entrant (rule 7).

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM", "PH")
# "Digital includes PSK, RTTY, Olivia, Packet, SSTV, ATV, JS8Call, and other
# soundcard modes except for FT4 & FT8." Winter Field Day does not allow them.
_NO_POINT_MODES = ("FT4", "FT8")

# The sponsor's Cabrillo spelling for the digital modes.
_DIGITAL_MODES = (
    "BPSK31",
    "CONTESTI",
    "DOMINO",
    "FSQ",
    "FT8",
    "FT4",
    "HELL",
    "IFKP",
    "RTTY",
    "PSK",
    "PSK31",
    "FSK441",
    "MFSK",
    "MSK144",
    "MT63",
    "OLIVIA",
    "JS8",
    "JT65",
    "JT9",
    "Q65",
    "SCAMP",
    "THOR",
    "THRB",
)


def _points_for_mode(mode: str) -> int:
    """Phone 1 point; CW and digital 2; FT4/FT8 score nothing."""
    upper = str(mode).upper()
    if not upper or upper in _NO_POINT_MODES:
        return 0
    if upper in _PHONE_MODES:
        return 1
    return 2


class Contest(ContestBase):
    """Winter Field Day."""

    DisplayName = "Winter Field Day"
    CabrilloName = "WFD"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "1O ORG"
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
    ]
    # The score is the points times the number of band/mode combinations worked,
    # not a keyed multiplier, so show_mults() is that count and the declared
    # slot only names the score-page row the module reported.
    NumMults = 1
    Multiplier1Name = "Prefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 4

    def points(self):
        """1 point phone, 2 CW or digital, nothing for FT4/FT8."""
        if self.parent.contact_is_dupe > 0:
            return 0
        return _points_for_mode(self.parent.contact.get("Mode", ""))

    def show_mults(self):
        """The number of band/mode combinations worked."""
        result = self.parent.database.get_unique_band_and_mode()
        return int(result.get("mult", 0)) if result else 0

    def calc_score(self):
        """The points times the combinations, doubled for a QRP entrant."""
        power = self.parent.contest_settings.get("PowerCategory", "")
        return super().calc_score() * (2 if power == "QRP" else 1)

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""

    def set_contact_vars(self):
        """The exchange; the class and section are the received ones."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = parent.other_1.text().upper()
        parent.contact["Sect"] = parent.other_2.text().upper()

    def prefill(self):
        """Nothing to prefill: other_1 is the class, not the sent exchange."""

    def cabrillo_mode(self, mode: str) -> str:
        """CW, PH or DG, as the sponsor spells them."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "FM", "AM"):
            return "PH"
        if str(mode).upper() in _DIGITAL_MODES:
            return "DG"
        return mode

    def cabrillo_qso_line(self, contact):
        """The Field Day line: the operator's own exchange, then class/section."""
        parent = self.parent
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        sent = parent.contest_settings.get("SentExchange", "").ljust(9).upper()
        return (
            f"QSO: {frequency} "
            f"{self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{sent}"
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Exchange1', '')).ljust(3)} "
            f"{str(contact.get('Sect', '')).ljust(6)}"
        )

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
        """Show the class, section and user text for the typed call."""
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
