"""CWO plugin

Find rules at: https://cwops.org/cwops-tests/

160-10m, once per band.  The exchange is a serial number and a name; each
callsign worked is a multiplier once for the contest.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """CWops Open (CWO)."""

    DisplayName = "CWOPS - Open"
    CabrilloName = "CW-OPEN"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# Name"
    SOAPBOX_HINT = """When completing the "Recd Number and Name" field, place a space between the received serial number
and the name of the other operator. eg. "123 Fred". (Advance on spacebar is disabled for this field.)
"""
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryFields = ("field3", "field4")
    FrameText = ("", "SentNR", "Recd Number and Name")
    AccessibleNames = ("", "", "Sent Number", "Received Number and Name")
    NextField = "other_2"
    # The received exchange is "number name", which contains a space.
    advance_on_space = [True, True, True, True, False]
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "Name",
        "M1",
        "PTS",
    ]
    PointsPerContact = 1
    # Each callsign once for the contest.
    NumMults = 1
    Multiplier1Name = "Calls"
    MultSqlString = "CallSign"
    IsMult1Per = 4

    def set_contact_vars(self):
        """Split the received "number name" into NR and Name."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()

        parts = parent.other_2.text().strip().split(maxsplit=1)
        if len(parts) == 2:
            if parts[0].isalpha():
                parent.contact["Name"] = parts[0].upper()
                parent.contact["NR"] = parts[1]
            elif parts[1].isalpha():
                parent.contact["Name"] = parts[1].upper()
                parent.contact["NR"] = parts[0]
        elif len(parts) == 1:
            if parts[0].isalpha():
                parent.contact["Name"] = parts[0].upper()
            else:
                parent.contact["NR"] = parts[0]
        self.mark_multipliers()

    def prefill(self):
        """Fill the sent serial, if the operator has not typed one."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The contact needs *both* exchange fields -- our serial and their number
        and name -- before it can be logged.
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

    def cabrillo_qso_line(self, contact):
        """The CWO line: serial, the operator's first name, then number and name."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{self.parent.station.get('Name', '').partition(' ')[0]} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
            f"{str(contact.get('Name', '')).ljust(10)} "
        )

    def ft8_handler(self, the_packet: dict):
        """Process a logged QSO packet from WSJT-X or FlDigi."""
        parent = self.parent
        their_name = the_packet.get("NAME", "").upper()
        their_nr = (
            the_packet.get("SRX_STRING", "") or the_packet.get("SRX", "")
        ).upper()
        our_nr = the_packet.get("STX", "") or parent.other_1.text()
        # Some loggers put the whole received exchange into SRX_STRING.
        if " " in their_nr:
            exchange = their_nr.split()[:2]
        else:
            exchange = [part for part in (their_nr, their_name) if part]
        their_name = next((part for part in exchange if part.isalpha()), "")
        their_nr = next((part for part in exchange if not part.isalpha()), "")
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.other_1.setText(our_nr)
        # set_contact_vars() re-parses this field as "number name" and only
        # copes with both halves being present.  Always overwrite it so a
        # partial packet cannot inherit the previous QSO's exchange, and rely
        # on the Name and NR set here when a half is missing.
        parent.other_2.setText(
            f"{their_nr} {their_name}" if their_nr and their_name else ""
        )
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = our_nr
        parent.contact["Name"] = their_name
        parent.contact["NR"] = their_nr
        parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

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
        """Put the operator's name, and a space after it, in the exchange field."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                name = result.get("Name", "")
                if name:
                    parent.other_2.setText(f"{name} ")
