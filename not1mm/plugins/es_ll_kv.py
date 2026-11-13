"""ES LL KV

Find rules at: https://erau.ee/images/LL/ES-Open_rules.pdf

A one-hour contest worked in four 15-minute periods: a station may be worked
again in each new period.  CW is worth 2 points and SSB 1.  The multiplier is
each Estonian call area -- the third character of the worked station's WPX
prefix -- once per band and mode, excluding the operator's own area.

The rules count the multipliers but do not apply them, so the claimed score is
the QSO points alone.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase, period_dupe_check
from not1mm.lib.ham_utility import calculate_wpx_prefix


class Contest(ContestBase):
    """ES LL KV."""

    DisplayName = "ES LL KV"
    CabrilloName = "ES-LL-KV"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    DupeType = 5  # a call again in each 15-minute period
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    # The reports, our serial and their serial.
    FrameText = ("", "Sent", "SN")
    AccessibleNames = ("", "", "Sent", "SN")
    # Each Estonian call area once per band and mode.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 3

    def specific_contest_check_dupe(self, call: str) -> dict:
        """A call per band and mode in each 15-minute period of the hour."""
        return period_dupe_check(self.parent, call, 60, 15)

    def points(self):
        """CW is worth 2 points, phone 1."""
        if self.parent.contact_is_dupe:
            return 0
        mode = self.parent.contact.get("Mode", "").upper()
        if mode in ("SSB", "USB", "LSB", "FM", "AM", "PH"):
            return 1
        if mode in ("CW", "CW-U", "CW-L", "CW-R", "CWR"):
            return 2
        return 0

    def mult_value(self, slot, contact):
        """The Estonian call area, from the third character of the prefix."""
        if slot == 1:
            if contact.get("CountryPrefix", "") != "ES":
                return None
            prefix = str(contact.get("WPXPrefix", "") or "")
            if not prefix:
                return None
            if prefix == calculate_wpx_prefix(self.parent.station.get("Call", "")):
                return None
            return prefix[2:3]
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            own = calculate_wpx_prefix(self.parent.station.get("Call", ""))
            return (
                "CASE WHEN CountryPrefix = 'ES' AND WPXPrefix <> "
                f"'{own}' THEN substr(WPXPrefix, 3, 1) END"
            )
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0

    def calc_score(self):
        """The QSO points; the multipliers are counted but not applied."""
        return self.just_points()

    def recalculate_mults(self):
        """Fill the call prefixes the multiplier and the ES filter read.

        An imported log carries neither for sure, so both are looked up from
        cty -- the pass the module made.  It marks no ``IsMultiplierN``: the
        column is not in this contest's log and the score counts from the log.
        """
        parent = self.parent
        for contact in parent.database.fetch_all_contacts_asc():
            result = parent.cty_lookup(contact.get("Call", ""))
            if result is None:
                continue
            item = result.get(next(iter(result)))
            contact["CountryPrefix"] = item.get("primary_pfx", "")
            contact["WPXPrefix"] = calculate_wpx_prefix(contact.get("Call", ""))
            parent.database.change_contact(contact)
