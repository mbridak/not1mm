"""ARRL January VHF plugin

Find rules at: http://www.arrl.org/january-vhf

50 MHz and up, once per band.  The exchange is the four-character grid square;
each grid square is a multiplier once per band, and a station outside the US and
Canada only scores W/VE contacts (rule 1).

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of, get_logged_band

# Rule 1: stations outside the US and Canada (and their possessions) may only
# work stations in the US, Canada and their possessions.  The contest page adds
# that stations in KH0-KH9, KL7, KP1-KP5, CY9 and CY0 count as W/VE.
WVE_PREFIXES = (
    "K",
    "KL",
    "KH0",
    "KH1",
    "KH2",
    "KH3",
    "KH4",
    "KH5",
    "KH6",
    "KH7",
    "KH8",
    "KH9",
    "KP1",
    "KP2",
    "KP3",
    "KP4",
    "KP5",
    "VE",
    "CY0",
    "CY9",
)

# The digital modes Cabrillo writes as "DG".
_DIGITAL = ("FT8", "FT4", "RTTY", "PSK31", "FSK441", "MSK144", "JT65", "JT9", "Q65")


class Contest(ContestBase):
    """ARRL January VHF."""

    DisplayName = "ARRL VHF JAN"
    CabrilloName = "ARRL-VHF-JAN"
    Mode = "BOTH"
    DupeType = 2  # once per band
    EXCHANGE_HINT = "4-character grid square"
    SupportsFT8 = True
    SendsRTCScore = True
    Bands = (50, 144, 222, 432, 902, 1296, 2300)
    # Only the sent and received grids are used; the RSTs are hidden.
    EntryFields = ("field3", "field4")
    FrameText = ("SNT", "Sent Grid", "Grid")
    AccessibleNames = ("RST Sent", "", "Sent Grid", "Gridsquare")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    # A grid square once per band (rule 5.3.1).
    NumMults = 1
    Multiplier1Name = "Grid"
    MultSqlString = "Grid"
    IsMult1Per = 1
    # January's point table (rule 5.1); June and September use 3 and 4.
    points_by_band = {50.0: 1, 144.0: 1, 222.0: 2, 432.0: 2, 902.0: 4, 1296.0: 4}
    high_band_points = 8
    # September reads the frequency as an integer; January and June do not.
    freq_is_int = False

    def _is_wve_station(self, call):
        """Is *call* in the US, Canada or their possessions (rule 1)?"""
        result = self.parent.cty_lookup(call)
        if result is None:
            return False
        item = result.get(next(iter(result)))
        return item.get("primary_pfx", "") in WVE_PREFIXES

    def points(self):
        """Points for the band, when either end is in W/VE (rule 1)."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if not self._is_wve_station(parent.station.get("Call", "")) and not (
            self._is_wve_station(parent.contact.get("Call", ""))
        ):
            return 0
        band = band_mhz_of(parent.contact.get("Band"))
        if band in self.points_by_band:
            return self.points_by_band[band]
        if band >= 2300.0:
            return self.high_band_points
        return 0

    def show_mults(self):
        """The number of grid squares, per band (rule 5.3.1).

        From outside W/VE only a W/VE station scores, so only their grids count
        -- which is a cty lookup per contact, not one query.
        """
        parent = self.parent
        if not self._is_wve_station(parent.station.get("Call", "")):
            mults = set()
            for contact in parent.database.fetch_all_contacts_asc():
                if self._is_wve_station(contact.get("Call", "")):
                    mults.add((contact.get("NR", ""), contact.get("Band")))
            return len(mults)
        sql = (
            "select count(DISTINCT(NR || ':' || Band)) as mult_count "
            f"from dxlog where ContestNR = {parent.database.current_contest} "
            "and typeof(NR) = 'text';"
        )
        result = parent.database.exec_sql(sql)
        return result.get("mult_count", 0) if result else 0

    def get_mults(self):
        """The score page wants the grid-square id."""
        return {"gridsquare": self.show_mults()}

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1`` (see §27)."""

    def set_contact_vars(self):
        """The sent and received grids; the RSTs are not used."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def cabrillo_qso_line(self, contact):
        """The VHF line: frequency to the MHz, and no RST.

        The base's line carries the RSTs and the full kHz frequency; this
        contest sends neither, and calls every digital mode ``DG``.
        """
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        freq = contact.get("Freq", "0")
        if self.freq_is_int:
            freq = int(freq)
        frequency = str(round(freq / 1000)).rjust(4)
        return (
            f"QSO: {frequency} {self._vhf_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
        )

    def _vhf_mode(self, mode):
        """The Cabrillo mode code: CW, PH or DG."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "AM"):
            return "PH"
        if mode in _DIGITAL:
            return "DG"
        return mode

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        my_grid = packet.get("MY_GRIDSQUARE", "")
        if my_grid:
            my_grid = my_grid[:4]
        their_grid = packet.get("GRIDSQUARE", "")
        if their_grid:
            their_grid = their_grid[:4]
        parent.contact["NR"] = their_grid
        parent.contact["Mode"] = packet.get("SUBMODE") or packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.other_1.setText(my_grid)
        parent.other_2.setText(their_grid)
        parent.save_contact()

    def populate_history_info_line(self):
        """Show history info if available."""
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
        """Prefill the received grid from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Loc1', '')}")
