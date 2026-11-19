"""LABRE-RS Digi Contest

Find rules at: https://labre-rs.org.br/labre-rs-digi-contest/
Upload logs at: https://hampass.org/contests

80, 40, 20, 15 and 10m, once per band, FT4/FT8.  The exchange is a four
character grid square.  A contact is one point, or two when the other station
is in the Brazilian third call area (PY3, PU3, ZZ3, PP3 or PX3), and the
multiplier is the first two characters of the received grid once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

# The digital modes the sponsor's log checker wants written as one Cabrillo
# mode.  Cabrillo itself knows only CW, PH, FM, RY and DG.
_DIGITAL_MODES = (
    "FT4",
    "FT8",
    "RTTY",
    "PSK31",
    "FSK441",
    "MSK144",
    "JT65",
    "JT9",
    "Q65",
)

# A station in the Brazilian third call area is worth a second point.
_PY3_PREFIXES = ("PY3", "PU3", "ZZ3", "PP3", "PX3")


class Contest(ContestBase):
    """LABRE-RS Digi Contest."""

    DisplayName = "LABRE-RS Digi"
    CabrilloName = "LABRE-RS-DIGI"
    Mode = "RTTY"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "4-character grid square"
    DupeType = 2  # 1 once per contest, 2 work each band, 3 each band/mode
    Bands = (3.5, 7, 14, 21, 28)
    SendsRTCScore = True
    SupportsFT8 = True
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    FrameText = ("SNT", "SentNR", "Grid")
    AccessibleNames = ("RST Sent", "", "Sent Grid", "Gridsquare")
    # The first two characters of the received grid, once per band.
    NumMults = 1
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1

    def points(self):
        """One point a contact, two for the Brazilian third call area."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if len(parent.contact.get("Call", "")) > 2:
            if parent.contact.get("Call", "")[:3] in _PY3_PREFIXES:
                return 2
        return 1

    def mult_sql(self, slot):
        """The first two characters of the received grid, as SQL."""
        if slot == 1:
            # A serial stored in the INTEGER column is not a grid.
            return "CASE WHEN typeof(NR) = 'text' THEN SUBSTR(NR, 1, 2) END"
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same key in Python, for a contact or a spot."""
        if slot == 1:
            grid = contact.get("NR", "")
            if not isinstance(grid, str) or not grid:
                return None
            return grid[:2].upper()
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The reports, the sent grid and the received grid; nothing is marked."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def recalculate_mults(self):
        """The module never marked a multiplier; the count reads the log."""

    def cabrillo_mode(self, mode):
        """The sponsor's digital modes are all ``DG``; phone is ``PH``."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "AM"):
            return "PH"
        if mode in _DIGITAL_MODES:
            return "DG"
        return mode

    def cabrillo_qso_line(self, contact):
        """The grid is the exchange: no reports, and the frequency in MHz."""
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

    def get_mults(self):
        """The score page files a grid-square count under `gridsquare`."""
        return {"gridsquare": self.show_mults()}

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = packet.get("RST_SENT", "59")
        parent.contact["RCV"] = packet.get("RST_RCVD", "59")

        my_grid = packet.get("MY_GRIDSQUARE", "")
        if len(my_grid) > 4:
            my_grid = my_grid[:4]
        their_grid = packet.get("GRIDSQUARE", "")
        if len(their_grid) > 4:
            their_grid = their_grid[:4]

        parent.contact["NR"] = their_grid
        if packet.get("SUBMODE"):
            parent.contact["Mode"] = packet.get("SUBMODE", "ERR")
        else:
            parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.other_1.setText(my_grid)
        parent.other_2.setText(their_grid)
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the call history file's entry for the callsign being typed."""
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
        """Fill the received grid from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Loc1', '')}")
