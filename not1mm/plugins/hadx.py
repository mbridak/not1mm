"""Hungarian DX Contest (HA-DX)

Find rules at: https://ha-dx.com/en/contest-rules

160-10m, once per band and mode.  An HA station sends a two-letter county, and
everyone else a serial number.  A Hungarian contact is worth 10 points, one on
the same continent 2 and another continent 5.  Each Hungarian county and each
DXCC/WAE country counts once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

# The counties an HA station may send.
HA_COUNTY = (
    "BA",
    "BE",
    "BN",
    "BO",
    "BP",
    "CS",
    "FE",
    "GY",
    "HB",
    "HE",
    "SZ",
    "KO",
    "NG",
    "PE",
    "SO",
    "SA",
    "TO",
    "VA",
    "VE",
    "ZA",
)

COUNTY_LIST = ", ".join(f"'{county}'" for county in HA_COUNTY)


class Contest(ContestBase):
    """Hungarian DX Contest."""

    DisplayName = "HA DX"
    CabrilloName = "HA-DX"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# or County"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The reports, our serial and their county or serial.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "SentNR", "HA County or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Hungarian county or Serial Number",
    )
    # Each Hungarian county and each country once per band.
    NumMults = 2
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    SendsRTCScore = True

    def points(self):
        """10 points for an HA station, else 2/5 by continent."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0
        if parent.contact.get("NR", "") in HA_COUNTY:
            return 10

        my_continent = ""
        their_continent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_continent = item.get("continent", "")

        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            their_continent = item.get("continent", "")

        if my_continent == their_continent:
            return 2
        return 5

    def mult_value(self, slot, contact):
        """A county when the exchange is text, a country when it is a serial."""
        if slot == 1:
            county = contact.get("NR")
            return county if county in HA_COUNTY else None
        if slot == 2:
            if isinstance(contact.get("NR"), int):
                return contact.get("CountryPrefix") or None
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same keys as SQL, for counting the log."""
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' AND Points = 10 THEN NR END"
        if slot == 2:
            return "CASE WHEN typeof(NR) = 'integer' THEN CountryPrefix END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's single row, as the module summed it."""
        return {"state": self.show_mults()}

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""
