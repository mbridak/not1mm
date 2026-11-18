"""RAC Canada Day Contest

Find rules at: https://www.rac.ca/canada-day-contest/

160-10m, once per band and mode.  A RAC official station is worth 20 points,
any other Canadian station 10 and a station outside Canada 2.  The multiplier
is each Canadian province or territory once per band and mode -- which is what
a Canadian station sends -- while a station elsewhere sends a serial number,
and a serial number is not a multiplier.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

RAC_OFFICIAL_STATIONS = (
    "VA2RAC",
    "VA3RAC",
    "VE1RAC",
    "VE4RAC",
    "VE5RAC",
    "VE6RAC",
    "VE7RAC",
    "VE8RAC",
    "VE9RAC",
    "VO1RAC",
    "VO2RAC",
    "VY0RAC",
    "VY1RAC",
    "VY2RAC",
    "VE3RHQ",
)


class Contest(ContestBase):
    """RAC Canada Day."""

    DisplayName = "CANADA DAY"
    CabrilloName = "CANADA-DAY"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Province/Territory"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The reports, our serial and their province/territory or serial.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "SentNR", "Prov/territory or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Province Territory or Serial Number",
    )
    # Each province/territory once per band and mode; a serial is not one.
    NumMults = 1
    Multiplier1Name = "Province/Territory"
    MultSqlString = "NR"
    IsMult1Per = 3

    def points(self):
        """20 for a RAC official station, 10 for Canada, 2 for anywhere else."""
        if self.parent.contact_is_dupe:
            return 0
        call = self.parent.contact.get("Call", "")
        if call in RAC_OFFICIAL_STATIONS:
            return 20
        result = self.parent.cty_lookup(call)
        if result is not None:
            item = result.get(next(iter(result)))
            if item.get("entity", "") == "Canada":
                return 10
        return 2

    def mult_value(self, slot, contact):
        """A province is text; a serial number is not a multiplier.

        ``NR`` is an INTEGER column, so a Canadian station's province is stored
        as text and a DX station's serial number as an integer.
        """
        if slot == 1:
            nr = contact.get("NR")
            if isinstance(nr, str) and nr and not nr.isdigit():
                return nr
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' AND NR != '' THEN NR END"
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""
