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
    EntryWindowInfo = ("SntNrText", 625, "Exchange1Text", 615)
    QsoErrorString = "SntNrText_Any_not_Empty, Exchange1Text_Any_not_Empty"
    FrameText = ("SentNR", "Recd Number and Name")
    AccessibleNames = (
        "Sent Number",
        "Received Number and Name",
    )
    # The received exchange is "number name", which contains a space.
    SpaceKeepsFocus = ("Exchange1Text",)
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
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()

        parts = parent.fields.Exchange1Text.text().strip().split(maxsplit=1)
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
        if len(parent.fields.SntNrText.text()) == 0:
            parent.fields.SntNrText.setText(serial_nr)

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
        our_nr = the_packet.get("STX", "") or parent.fields.SntNrText.text()
        # Some loggers put the whole received exchange into SRX_STRING.
        if " " in their_nr:
            exchange = their_nr.split()[:2]
        else:
            exchange = [part for part in (their_nr, their_name) if part]
        their_name = next((part for part in exchange if part.isalpha()), "")
        their_nr = next((part for part in exchange if not part.isalpha()), "")
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.fields.SntNrText.setText(our_nr)
        # set_contact_vars() re-parses this field as "number name" and only
        # copes with both halves being present.  Always overwrite it so a
        # partial packet cannot inherit the previous QSO's exchange, and rely
        # on the Name and NR set here when a half is missing.
        parent.fields.Exchange1Text.setText(
            f"{their_nr} {their_name}" if their_nr and their_name else ""
        )
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
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
            if parent.fields.Exchange1Text.text() == "":
                name = result.get("Name", "")
                if name:
                    parent.fields.Exchange1Text.setText(f"{name} ")
