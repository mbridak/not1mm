"""CQ World Scout

Find rules at: https://www.escoteiros.org.br/wp-content/uploads/2026/02/Boletim_CQWS_2026_ingles.pdf

Each station may be worked once per band.  The received exchange is the station
type, which sets the points (and is the Brazilian Federal Unit multiplier once
per band); each distinct country is a second multiplier, counted once for the
contest.
"""

import logging

from not1mm.lib.contest import ContestBase

logger = logging.getLogger(__name__)

# The station type sets the points.  A Brazilian Federal Unit is worth 1, the
# special club/event stations 3 to 10.
STATION_POINTS = {
    "AC": 1,
    "AL": 1,
    "AP": 1,
    "AM": 1,
    "BA": 1,
    "CE": 1,
    "DF": 1,
    "ES": 1,
    "GO": 1,
    "MA": 1,
    "MT": 1,
    "MS": 1,
    "MG": 1,
    "PA": 1,
    "PB": 1,
    "PR": 1,
    "PE": 1,
    "PI": 1,
    "RJ": 1,
    "RS": 1,
    "RO": 1,
    "RN": 1,
    "RR": 1,
    "SC": 1,
    "SP": 1,
    "SE": 1,
    "TO": 1,
    "CL": 3,
    "HQ": 3,
    "RA": 3,
    "DX": 3,
    "PT": 5,
    "BP": 5,
    "RE": 5,
    "GE": 5,
    "DB": 5,
    "FD": 7,
    "YL": 7,
    "QRP": 7,
    "WS": 10,
}


class Contest(ContestBase):
    """CQ World Scout."""

    DisplayName = "CQ WORLD SCOUT"
    CabrilloName = "CQWS"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Station Type"
    DupeType = 2  # once per band
    # The reports and the station type; other_1 is unused.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "Station type")
    AccessibleNames = ("RST Sent", "", "", "Received Exchange")
    NextField = "other_2"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "RcvNr",
        "PTS",
    ]
    # The Brazilian Federal Unit once per band, and each country once for the
    # contest.
    NumMults = 2
    Multiplier1Name = "UF"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "Country"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 4

    def mult_sql(self, slot):
        """The Federal Unit as SQL; a contact worth no points is not a mult."""
        if slot == 1:
            return "CASE WHEN Points > 0 THEN NR END"
        return super().mult_sql(slot)

    def points(self):
        """The station type sets the points; a dupe is worth nothing."""
        if self.parent.contact_is_dupe:
            return 0
        return STATION_POINTS.get(str(self.parent.contact.get("NR", "")).upper(), 0)

    def set_contact_vars(self):
        """The reports and the station type; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        parent.contact["NR"] = parent.other_2.text()

    def prefill(self):
        """Nothing to fill: the sent exchange is a fixed setting."""

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""

    def calc_score(self):
        """The sponsor's score: the points times (1 + the multipliers)."""
        result = self.parent.database.fetch_points()
        points = int(result.get("Points") or 0) if result is not None else 0
        return points * (1 + self.show_mults())

    def populate_history_info_line(self):
        """Not used: this contest has no call history entry."""

    def check_call_history(self):
        """Not used: this contest has no call history entry."""
