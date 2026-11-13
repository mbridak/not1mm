"""CQ World-Wide DX Contest, CW

Find rules at: https://www.cqww.com/rules/

160-10m, once per band.  A contact across continents is worth 3 points, 2
inside North America between two countries, 1 on one continent between two
countries and 0 inside a country -- a country contact still counts for the
multipliers, which are each CQ zone and each DXCC country once per band.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """CQ World-Wide DX Contest, CW."""

    DisplayName = "CQ WW CW"
    CabrilloName = "CQ-WW-CW"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "CQ Zone No."
    DupeType = 2  # once per band
    SendsRTCScore = True
    # The reports, the fixed sent exchange (other_1 is hidden) and their zone.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "CQ Zone")
    AccessibleNames = ("RST Sent", "", "", "C Q Zone")
    # Each country and each zone once per band.
    NumMults = 2
    Multiplier1Name = "Country"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    Multiplier2Name = "CQ Zone"
    MultSqlString2 = "CQZONE"
    IsMult2Per = 1

    def points(self):
        """3 across continents, 2 inside NA, 1 on one continent, 0 at home."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        mine = parent.cty_lookup(parent.station.get("Call", ""))
        if mine is None:
            return 0
        item = mine.get(next(iter(mine)))
        mycountry = item.get("entity", "")
        mycontinent = item.get("continent", "")
        theirs = parent.cty_lookup(parent.contact.get("Call", ""))
        if theirs is not None:
            item = theirs.get(next(iter(theirs)))
            entity = item.get("entity", "")
            continent = item.get("continent", "")
            # Different continents count three.
            if mycontinent != continent:
                return 3
            # Different countries inside North America count two.
            if mycontinent == "NA" and mycountry != entity:
                return 2
            # Different countries on one continent count one.
            if mycountry.upper() != entity.upper():
                return 1
        return 0

    def mult_value(self, slot, contact):
        """The DXCC country, with IG9/IH9 apart from Italy and /MM out."""
        if slot == 1:
            call = str(contact.get("Call", "")).upper()
            if call.endswith("/MM") or call.startswith("MM/"):
                return None
            prefix = contact.get("CountryPrefix", "")
            if prefix == "I" and call[:3] in ("IG9", "IH9"):
                prefix = call[:3]
            return prefix
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same country key as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN Call LIKE '%/MM' OR Call LIKE 'MM/%' THEN NULL "
                "WHEN CountryPrefix = 'I' "
                "AND upper(substr(Call, 1, 3)) IN ('IG9', 'IH9') "
                "THEN upper(substr(Call, 1, 3)) "
                "ELSE CountryPrefix END"
            )
        return super().mult_sql(slot)

    def prefill(self):
        """Fill the zone from a call lookup; the sent exchange is fixed."""
        parent = self.parent
        if len(parent.other_2.text()) == 0:
            parent.other_2.setText(str(parent.contact.get("ZN", "")))
        parent.other_1.setText(str(parent.contest_settings.get("SentExchange", 0)))

    def set_contact_vars(self):
        """The reports, the received zone and the fixed sent exchange."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["ZN"] = parent.other_2.text()
        parent.contact["NR"] = parent.other_2.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)

    def recalculate_mults(self):
        """No marks: the multipliers are counted from the log (see show_mults)."""

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('CQZone', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the zone from the call history entry."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('CQZone', '')}")
