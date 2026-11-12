"""CQ 160-Meter SSB Contest

Find rules at: https://www.cq160.com/rules/

160m only, once for the whole contest.  A contact is worth 2 points inside
one's own country, 5 within the continent and 10 across continents, and a
maritime mobile always 5.  The multiplier is each US state, each Canadian
province and each DXCC country, counted once for the contest.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """CQ 160-Meter SSB Contest."""

    DisplayName = "CQ 160 SSB"
    CabrilloName = "CQ-160-SSB"
    Mode = "SSB"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "ST/Prov or DX CQ Zone"
    DupeType = 1  # once per contest
    Bands = (1.8,)
    # The reports, the fixed sent exchange (other_1 is hidden) and their
    # state, province or CQ zone.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "ST/Prov/CQ Zone")
    AccessibleNames = ("RST Sent", "", "", "Received Exchange")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "PFX",
        "RcvNr",
        "M1",
        "PTS",
    ]
    # A W/VE station is keyed on the state or province it sends and everyone
    # else on their DXCC prefix.  The pair keeps "K:DL" (a US station sending
    # "DL" by mistake) from colliding with the country "DL".
    NumMults = 1
    Multiplier1Name = "State/Province/Country"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 4

    def points(self):
        """10 across continents, 5 within one, 2 inside a country, /MM 5."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if "/MM" in parent.contact.get("Call", ""):
            return 5
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
            if mycountry.upper() == entity.upper():
                return 2
            if mycontinent == continent:
                return 5
            return 10
        return 0

    def mult_value(self, slot, contact):
        """The state/province a W/VE station sends, else the DXCC prefix.

        A maritime mobile is not a multiplier, which is why it is spelled out
        here rather than left to the prefix.
        """
        if slot == 1:
            if "/MM" in str(contact.get("Call", "")):
                return None
            prefix = contact.get("CountryPrefix", "")
            if prefix in ("K", "VE"):
                return f"{prefix}:{contact.get('NR', '')}"
            return prefix
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN Call LIKE '%/MM' THEN NULL "
                "WHEN CountryPrefix IN ('K', 'VE') "
                "THEN CountryPrefix || ':' || NR "
                "ELSE CountryPrefix END"
            )
        return super().mult_sql(slot)

    def prefill(self):
        """Nothing to fill: the sent exchange is the fixed contest setting."""

    def set_contact_vars(self):
        """The reports, the fixed sent exchange and the received zone."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", "")
        parent.contact["NR"] = parent.other_2.text()
        self.mark_multipliers()

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the received exchange from the call history entry."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
