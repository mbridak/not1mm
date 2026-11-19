"""ARRL DX CW plugin

Find rules at: https://contests.arrl.org/ContestRules/DX-Rules.pdf

160/80/40/20/15/10m, once per band.  W/VE sends its state or province, the rest
of the world sends power.  A contact between W/VE and the rest is worth 3
points; W/VE counts each DXCC country worked per band, everyone else counts each
W/VE state/province per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# The two sides of the contest.
_WVE = ("K", "VE")


class Contest(ContestBase):
    """ARRL DX, CW."""

    DisplayName = "ARRL DX CW"
    CabrilloName = "ARRL-DX-CW"
    Mode = "CW"
    DupeType = 2  # once per band
    EXCHANGE_HINT = "State/Province"
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # other_1 is not used; the whole exchange is the received power/state.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "Power/State/Province")
    AccessibleNames = ("RST Sent", "", "", "Power or state or province")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "RcvNr",
        "M1",
        "PFX",
        "PTS",
    ]
    # W/VE counts each DXCC country per band and the rest each W/VE
    # state/province, and only a contact that scores is a multiplier -- so the
    # key is a CASE over the points, and the side decides the column.
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    my_country = ""

    def init_contest(self):
        """Set up the entry window, then work out which side we are on."""
        super().init_contest()
        item = self._entity(self.parent.station.get("Call", "")) or {}
        self.my_country = item.get("primary_pfx", "")

    def _entity(self, call):
        """The cty.dat entry for *call*, or None."""
        result = self.parent.cty_lookup(call)
        if result is None:
            return None
        return result.get(next(iter(result)))

    @property
    def is_wve(self):
        """Are we the W/VE side of the contest?"""
        return self.my_country in _WVE

    def points(self):
        """3 points for a W/VE-to-DX contact, else 0."""
        if self.parent.contact_is_dupe > 0:
            return 0
        item = self._entity(self.parent.contact.get("Call", ""))
        if item is None:
            return 0
        if self.is_wve == (item.get("primary_pfx", "") in _WVE):
            return 0
        return 3

    def mult_value(self, slot, contact):
        """The key: the DXCC country from W/VE, the state/province from DX.

        A logged contact carries its ``Points`` and only a scoring one is a
        multiplier; the contact being logged does not, so the live check is
        left to the SQL in :meth:`mult_sql`, which counts only scoring ones.
        """
        points = contact.get("Points")
        if points is not None and int(points or 0) != 3:
            return None
        column = "CountryPrefix" if self.is_wve else "NR"
        return contact.get(column, "") or None

    def mult_sql(self, slot):
        """The same key as SQL, over the contacts that score."""
        column = "CountryPrefix" if self.is_wve else "NR"
        return f"CASE WHEN points = 3 THEN {column} END"

    def get_mults(self):
        """The score page wants both ids; only the one we count is non-zero."""
        count = self.show_mults()
        if self.is_wve:
            return {"country": count, "state": 0}
        return {"country": 0, "state": count}

    def set_contact_vars(self):
        """The exchange, and the multiplier the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        self.mark_multipliers()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('Power', '')}, "
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
            if parent.other_2.text() == "":
                if result.get("State", ""):
                    parent.other_2.setText(f"{result.get('State', '')}")
                if result.get("Power", ""):
                    parent.other_2.setText(f"{result.get('Power', '')}")
