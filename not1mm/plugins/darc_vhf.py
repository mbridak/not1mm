"""DARC VHF and above

Find rules at: https://www.darc.de/der-club/referate/conteste/ukw/tnukwcontest001/tnukwcontest007000/

145 MHz and up, once per band.  The exchange is RST and a locator, and a
contact scores one point per kilometre between the two stations.  There are no
multipliers: the score is the sum of the distances.  The log is EDI.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from PyQt6 import QtWidgets

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import distance
from not1mm.lib.plugin_common import gen_edi

_DIGITAL_MODES = {
    "FT8",
    "FT4",
    "RTTY",
    "PSK31",
    "FSK441",
    "MSK144",
    "JT65",
    "JT9",
    "Q65",
    "PKTUSB",
    "PKTLSB",
}


def _dupe_mode(mode: str) -> str:
    """Group a mode the way the band/mode duplicate check does."""

    mode = str(mode).upper()
    if mode in ("LSB", "USB", "SSB", "FM", "AM"):
        return "PH"
    if mode.startswith("CW"):
        return "CW"
    if mode in _DIGITAL_MODES:
        return "DI"
    return "OTHER"


class Contest(ContestBase):
    """DARC VHF and above."""

    DisplayName = "DARC VHF"
    CabrilloName = "DARC VHF"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# + 6char grid"
    DupeType = 3  # work each band/mode once
    WritesEDI = True
    # The received exchange is "# grid", so a space is part of it; the label
    # follows what was typed (see parse_exchange).
    advance_on_space = [True, True, True, True, False]
    call_parse_exchange_on_edit = True
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "PTS",
    ]
    FrameText = ("SNT", "SentNR", "# Grid")
    AccessibleNames = ("RST Sent", "", "Sent Number", "Gridsquare")

    def reset_label(self):
        """Put the exchange label back after the field is cleared."""
        self.parent.exch_label.setText(
            QtWidgets.QApplication.translate("ContestPlugin", "# Grid")
        )

    def parse_exchange(self):
        """Parse the typed exchange into the serial and the 6-character grid."""
        parent = self.parent
        exchange = parent.other_2.text().upper()
        sn = ""
        grid = ""
        for token in exchange.split():
            if token.isdigit():
                if sn == "":
                    sn = token
                continue
            if token.isalnum():
                if len(token) == 6:
                    grid = token
                continue
        parent.exch_label.setText(f"Sn:{sn} Grid:{grid}")
        return (sn, grid)

    def points(self):
        """One point per kilometre between the two stations."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        their_grid = str(parent.contact.get("Exchange1", "") or "").upper()
        kilometers = distance(parent.station.get("GridSquare", ""), their_grid)
        return max(1, kilometers)

    def set_contact_vars(self):
        """The typed "# grid" is split into the serial and the locator."""
        parent = self.parent
        sn, grid = self.parse_exchange()
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = sn
        parent.contact["Exchange1"] = grid

    def cabrillo_qso_line(self, contact):
        """The locator is a field of its own in this contest's log."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).upper().ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).ljust(6)} "
            f"{str(contact.get('Exchange1', '')).ljust(6)}"
        )

    def recalculate_mults(self):
        """Rescore the log: the distance, and a duplicate is worth nothing.

        The distance depends on the operator's own grid, so the points are
        worked out again; the duplicate is per band and mode, and a duplicate
        used to be scored like any other contact.
        """
        parent = self.parent
        worked = set()
        for contact in parent.database.fetch_all_contacts_asc():
            parent.contact = contact
            key = (
                str(contact.get("Call", "")).upper(),
                contact.get("Band", ""),
                _dupe_mode(contact.get("Mode", "")),
            )
            parent.contact_is_dupe = 1 if key in worked else 0
            worked.add(key)
            contact["Points"] = self.points()
            parent.database.change_contact(contact)

    def edi(self):
        """Write the EDI log the sponsor wants."""
        parent = self.parent
        value = parent.contest_settings.get("StartDate", "")
        start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
        gen_edi(
            parent,
            self.CabrilloName,
            "DARC VHF Contest",
            start_date,
            start_date,
        )

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        Both exchange fields -- the sent locator and the received "# grid" --
        are needed before the contact can be logged.
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

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Exch1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the sent locator from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Exch1', '')}")
