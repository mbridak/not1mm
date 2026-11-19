"""EU DX Contest (EUDXC)

Find rules at: https://www.eudx-contest.com/rules/

160-10m, once per band and mode.  A European Union flag is raised by the
received exchange being a four-character region code ("DE01"); everyone else
sends an ITU zone.  An EU contact is worth 10 points, the operator's own
country 2, another country on the same continent 3 and another continent 5.
Each DXCC country and each EU region counts once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


def _is_eu_region(exchange) -> bool:
    """True for a four-character European Union region code ("DE01")."""
    exchange = str(exchange).strip()
    return len(exchange) == 4 and exchange[:2].isalpha() and exchange[2:].isdigit()


class Contest(ContestBase):
    """EU DX Contest."""

    DisplayName = "EUDXC"
    CabrilloName = "EUDXC"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "ITU or EU Union Region"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The reports, our region or ITU zone and theirs.
    FrameText = ("SNT", "SentNR", "ITU/EU Union Region")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "I T U Section or E U Union Region",
    )
    # Each DXCC country and each EU region once per band.
    NumMults = 2
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    Multiplier2Name = "NR"
    MultSqlString2 = "NR"
    IsMult2Per = 1
    SendsRTCScore = True

    def points(self):
        """10 points for an EU station, 2 own country, 3/5 by continent."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0

        my_country = ""
        my_continent = ""
        their_country = ""
        their_continent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_country = item.get("entity", "")
            my_continent = item.get("continent", "")

        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            their_country = item.get("entity", "")
            their_continent = item.get("continent", "")

        if my_country == their_country:
            return 2
        if _is_eu_region(parent.contact.get("NR", "")):
            return 10
        if my_continent == their_continent:
            return 3
        return 5

    def mult_value(self, slot, contact):
        """The EU region, when the exchange is one; the country is a column."""
        if slot == 2:
            exchange = contact.get("NR")
            return str(exchange) if _is_eu_region(exchange) else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same region key as SQL, for counting the log."""
        if slot == 2:
            return "CASE WHEN NR GLOB '[A-Za-z][A-Za-z][0-9][0-9]' THEN NR END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's two rows, as the module grouped them."""
        return {"country": self._mult_count(2), "state": self._mult_count(1)}

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text().upper()

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""

    def populate_history_info_line(self):
        """Show history info if available."""
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
        """Prefill the received exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
