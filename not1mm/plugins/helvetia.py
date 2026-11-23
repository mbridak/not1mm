"""Helvetia Contest

Find rules at: https://www.uska.ch/contests/concours-helvetia/

160-10m, once per band and mode.  An HB station sends a two-letter canton and
everyone else a serial number.  A Swiss contact is worth 10 points, one on the
same continent 1 and another continent 3.  Each canton and each DXCC country
counts once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

# The cantons an HB station may send.
CANTONS = (
    "AG",
    "AI",
    "AR",
    "BE",
    "BL",
    "BS",
    "CH",
    "FR",
    "GE",
    "GL",
    "GR",
    "JU",
    "LU",
    "NE",
    "NW",
    "OW",
    "SG",
    "SH",
    "SO",
    "SZ",
    "TG",
    "TI",
    "UR",
    "VD",
    "VS",
    "ZG",
    "ZH",
)


class Contest(ContestBase):
    """Helvetia Contest."""

    DisplayName = "HELVETIA"
    CabrilloName = "HELVETIA"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    PointsRules = "HB, 10, SameContinent, 1, OtherContinent, 3"
    EXCHANGE_HINT = "Canton or #"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]
    # The reports, our canton or serial and theirs.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    FrameText = ("SNT", "RCV", "Sent", "Canton/SN")
    AccessibleNames = ("", "", "Sent", "Canton or SN")
    # Each canton and each DXCC country once per band.
    NumMults = 2
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    SendsRTCScore = True

    def _entity(self, call):
        """Return ``(entity, continent)`` for a callsign, or ``("", "")``."""
        result = self.parent.cty_lookup(call)
        if not result:
            return "", ""
        item = result.get(next(iter(result)), {})
        return item.get("entity", ""), item.get("continent", "")

    def mult_value(self, slot, contact):
        """The canton when an HB station sent one; the country is a column."""
        if slot == 1:
            canton = contact.get("NR")
            if (
                contact.get("CountryPrefix") == "HB"
                and isinstance(canton, str)
                and canton.isalpha()
            ):
                return canton.upper()
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same canton key as SQL; a serial is not a multiplier."""
        if slot == 1:
            return (
                "CASE WHEN CountryPrefix = 'HB' "
                "AND typeof(NR) = 'text' AND NR <> '' THEN upper(NR) END"
            )
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange, then mark the two multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["SentNr"] = parent.fields.SntNrText.text().upper()
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()
        self.mark_multipliers()

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        if self.parent.log_window:
            self.parent.log_window.msg_from_main({"cmd": "UPDATELOG"})

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Exch1', '')}")
