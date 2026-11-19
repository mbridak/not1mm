"""ICWC Medium Speed Test

Find rules at: https://internationalcwcouncil.org/mst-contest/

160-10m, once per band.  The exchange is the other operator's name and their
QSO number; each callsign worked is a multiplier once for the contest.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """ICWC Medium Speed Test."""

    DisplayName = "ICWC Medium Speed Test"
    CabrilloName = "ICWC-MST"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "NAME"
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    SendsRTCScore = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryFields = ("field3", "field4")
    FrameText = ("", "Sent S/N", "Name + S/N")
    AccessibleNames = ("", "", "Sent Serial Number", "Name and Serial Number")
    NextField = "other_2"
    # The exchange is "name number", which contains a space.
    advance_on_space = [True, True, True, True, False]
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "SentNr",
        "Name",
        "RcvNr",
        "PTS",
    ]
    PointsPerContact = 1
    # Each callsign once for the contest.
    NumMults = 1
    Multiplier1Name = "Calls"
    MultSqlString = "CallSign"
    IsMult1Per = 4

    def set_contact_vars(self):
        """The sent serial and the split name/number; this contest marks no mults."""
        parent = self.parent
        parent.contact["SNT"] = "599"
        parent.contact["RCV"] = "599"
        parent.contact["SentNr"] = parent.other_1.text()
        exchange = parent.other_2.text().upper()
        if " " in exchange:
            parent.contact["Name"], parent.contact["NR"] = exchange.split(" ")
        else:
            parent.contact["Name"] = exchange

    def prefill(self):
        """Fill the sent serial, if the operator has not typed one."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""

    def cabrillo_qso_line(self, contact):
        """The MST line: the sent exchange, the serial, then name and number."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{self.parent.contest_settings.get('SentExchange', '').ljust(14).upper()}"
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Name', '')).ljust(14)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
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
            exchange = [part for part in (their_name, their_nr) if part]
        their_name = next((part for part in exchange if part.isalpha()), "")
        their_nr = next((part for part in exchange if not part.isalpha()), "")
        # set_contact_vars() splits this field on a single space into Name and
        # NR, and treats a lone word as the Name, so hand it "name number"
        # when both were copied, just the name when only that was, and nothing
        # when only the number was (NR set below then survives).
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.other_1.setText(our_nr)
        parent.other_2.setText(
            f"{their_name} {their_nr}" if their_name and their_nr else their_name
        )
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = "599"
        parent.contact["RCV"] = "599"
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
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the received name/number field from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Name', '')}")
