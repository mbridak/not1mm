"""K1USN Slow Speed Test

Find rules at: http://www.k1usn.com/sst.html

160-10m, once per band.  The exchange is the operator's name and their
state/province/country; each one of those is a multiplier once per band, and a
station outside W/VE is not a country multiplier of its own.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """K1USN Slow Speed Test."""

    DisplayName = "K1USN SLOW SPEED TEST"
    CabrilloName = "K1USNSST"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name + SPC"
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    SendsRTCScore = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryWindowInfo = ("NameText", 855, "SectText", 600)
    QsoErrorString = "NameText_Any_not_Empty, SectText_Any_not_Empty"
    FrameText = ("Name", "SPC")
    AccessibleNames = (
        "Name",
        "SPC",
    )
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Name",
        "Sect",
        "M1",
        "PTS",
    ]
    PointsPerContact = 1
    # Each state/province/country once per band.
    NumMults = 1
    Multiplier1Name = "SPC"
    MultSqlString = "Sect"
    IsMult1Per = 1

    def mult_sql(self, slot):
        """The section as SQL, dropping the "DX" a non-W/VE station sends."""
        if slot == 1:
            return "CASE WHEN Sect != 'DX' THEN Sect END"
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The state/province/country; "DX" is not one."""
        if slot == 1:
            sect = contact.get("Sect", "")
            return sect if sect and sect != "DX" else None
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The name and state/province/country, and the multiplier mark."""
        parent = self.parent
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Name"] = parent.fields.NameText.text().upper()
        parent.contact["Sect"] = parent.fields.SectText.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        self.mark_multipliers()

    def prefill(self):
        """Nothing to fill: the sent exchange is a fixed setting."""

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def cabrillo_qso_line(self, contact):
        """The SST line: the sent exchange, then their name and SPC."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).upper()} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Name', '')).ljust(11)} "
            f"{str(contact.get('Sect', '')).ljust(5)}"
        )

    def ft8_handler(self, the_packet: dict):
        """Process a logged QSO packet from WSJT-X or FlDigi."""
        parent = self.parent
        their_name = the_packet.get("NAME", "").upper()
        their_spc = (
            the_packet.get("STATE", "") or the_packet.get("SRX_STRING", "") or "DX"
        ).upper()
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.fields.NameText.setText(their_name)
        parent.fields.SectText.setText(their_spc)
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Name"] = their_name
        parent.contact["Sect"] = their_spc
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
        """Fill the exchange from the call history file, if it has one."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.NameText.text() == "":
                parent.fields.NameText.setText(f"{result.get('Name', '')}")
            if parent.fields.SectText.text() == "":
                parent.fields.SectText.setText(f"{result.get('Exch1', '')}")
