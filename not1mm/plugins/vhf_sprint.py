"""VHF SPRINT

Find rules at: https://sites.google.com/site/springvhfupsprints/home/2026-information

The VHF & Up Sprints: on 50, 144, 222 and 432 MHz a contact is one point, on
the Microwave Sprint (902 MHz and above) it is the distance in kilometres, at
least one.  The multiplier is each locator worked once per band, whatever mode
it was worked on, and the score is the points times the multipliers.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of, distance, get_logged_band


class Contest(ContestBase):
    """VHF & Up Sprints."""

    DisplayName = "VHF SPRINT"
    CabrilloName = "VHF-SPRINT"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "4-character grid square"
    DupeType = 3  # work each band/mode once
    SupportsFT8 = True
    SendsRTCScore = True
    Bands = (50, 144, 222, 432, 902, 1296, 2300, 3300, 5650, 10000, 24000, 47000)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    # Only the two locator fields are shown: the reports are not part of the
    # exchange in this contest.
    EntryFields = ("field3", "field4")
    FrameText = ("SNT", "Sent Grid", "Grid")
    AccessibleNames = ("RST Sent", "", "Sent Grid", "Gridsquare")
    NumMults = 1
    Multiplier1Name = "Grid"
    MultSqlString = "NR"
    IsMult1Per = 1  # once per band
    DefaultContestExchange = "#"

    def mult_sql(self, slot: int):
        """A locator is the exchange only when it is text, not a serial.

        ``NR`` is an INTEGER column, so a number stored there is not a locator:
        the module's own query filtered on ``typeof(NR) = 'text'``.
        """
        return "CASE WHEN typeof(NR) = 'text' THEN NR END"

    def set_contact_vars(self):
        """The locator is the received exchange; the RST fields are hidden."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text().upper()

    def points(self):
        """One point a contact below 902 MHz, the distance above it."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        band = band_mhz_of(parent.contact.get("Band"))
        if band in (50.0, 144.0, 222.0, 432.0):
            return 1
        if band in (902.0, 1296.0) or band >= 2300.0:
            their_grid = str(parent.contact.get("NR", "") or "").upper()
            return max(1, distance(parent.station.get("GridSquare", ""), their_grid))
        return 0

    def cabrillo_qso_line(self, contact):
        """The frequency is written in MHz and the reports are left out."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0") / 1000)).rjust(4)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
        )

    def cabrillo_mode(self, mode: str) -> str:
        """The sponsor's mode codes: the digital modes are ``DG``."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "AM"):
            return "PH"
        if mode in (
            "FT8",
            "FT4",
            "RTTY",
            "PSK31",
            "FSK441",
            "MSK144",
            "JT65",
            "JT9",
            "Q65",
        ):
            return "DG"
        return mode

    def recalculate_mults(self):
        """The module never marked its multipliers; the count reads the log."""

    def get_mults(self):
        """The score page files the locators under ``gridsquare``."""
        return {"gridsquare": self.show_mults()}

    def ft8_handler(self, the_packet: dict):
        """Take a QSO from WSJT-X/FlDigi."""
        parent = self.parent
        parent.callsign.setText(the_packet.get("CALL"))
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        my_grid = the_packet.get("MY_GRIDSQUARE", "")
        if my_grid:
            if len(my_grid) > 4:
                my_grid = my_grid[:4]
        their_grid = the_packet.get("GRIDSQUARE", "")
        if their_grid:
            if len(their_grid) > 4:
                their_grid = their_grid[:4]
        parent.contact["NR"] = their_grid
        if the_packet.get("SUBMODE"):
            parent.contact["Mode"] = the_packet.get("SUBMODE", "ERR")
        else:
            parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.other_1.setText(my_grid)
        parent.other_2.setText(their_grid)
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Loc1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received locator from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Loc1', '')}")
