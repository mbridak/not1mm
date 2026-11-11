"""ALL ASIA CW plugin

Find rules at: https://www.jarl.org/English/4_Library/A-4-3_Contests/aadx_eng.html

160/80/40/20/15/10m, RST + age (or 01), once per band.  Both the points and the
multiplier depend on which side of the contest the operator is on: from Asia
every station scores and each DXCC entity per band is a multiplier, from
outside only an Asian station scores and each Asian prefix per band is one.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import calculate_wpx_prefix


class Contest(ContestBase):
    """All Asia DX, CW."""

    DisplayName = "AADX CW"
    CabrilloName = "AADX-CW"
    Mode = "CW"
    EXCHANGE_HINT = "age (or 01)"
    ADIFContestID = "AADX-CW"
    SendsRTCScore = True
    advance_on_space = [True, True, True, True, True]
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "PTS",
    ]
    # The multiplier is a DXCC entity from Asia and an Asian prefix from
    # outside, so the key is a method; it counts once per band.  The score page
    # has always been told "wpxprefix", and keeps being told that.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 1
    # Which side of the contest we are on, worked out in init_contest.
    my_continent = ""
    my_country = ""

    def init_contest(self):
        """Set up the entry window, then work out which side we are on."""
        super().init_contest()
        result = self.parent.cty_lookup(self.parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            self.my_country = item.get("entity", "")
            self.my_continent = item.get("continent", "")

    def _entity(self, call):
        """The cty entry for *call*, or None."""
        result = self.parent.cty_lookup(call)
        if result is None:
            return None
        return result.get(next(iter(result)))

    def points(self):
        """Points for the contact being logged: a band matrix, by continent.

        The logged frequency decides the band: 160m is worth three times an
        ordinary band, 80m and 10m twice.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        contact = parent.contact
        item = self._entity(contact.get("Call", ""))
        if item is None:
            return 0
        their_country = item.get("entity", "")
        their_continent = item.get("continent", "")
        band = int(int(float(contact.get("Freq", 0))) / 1000)

        if self.my_country.upper() == their_country.upper():
            return 0

        # From Asia everyone scores; an outsider is worth more.
        if self.my_continent == "AS":
            multiplier = 3 if their_continent != "AS" else 1
        elif their_continent == "AS":
            # From outside, only an Asian station scores.
            multiplier = 1
        else:
            return 0
        if band == 1:
            return 3 * multiplier
        if band in (3, 28):
            return 2 * multiplier
        return multiplier

    def mult_value(self, slot, contact):
        """The multiplier key: a DXCC entity from Asia, an Asian prefix outside.

        The operator's own entity never counts, and from outside only an Asian
        station does -- which is what makes the key a method rather than a
        column.  The prefixes are looked up rather than read off the contact:
        an imported log does not carry them.
        """
        item = self._entity(contact.get("Call", ""))
        if item is None:
            return None
        if self.my_country.upper() == item.get("entity", "").upper():
            return None
        if self.my_continent == "AS":
            return item.get("primary_pfx", "") or None
        if item.get("continent", "") != "AS":
            return None
        return calculate_wpx_prefix(contact.get("Call", "")) or None

    def show_mults(self):
        """The number of multipliers is the number of marked contacts.

        The key is conditional (an entity from Asia, a prefix from outside), so
        the log cannot be counted by one query; the marks are the count.
        """
        result = self.parent.database.fetch_mult_count(1)
        return int(result.get("count", 0)) if result else 0

    def mark_multipliers(self):
        """Set ``IsMultiplier1`` on the contact being logged.

        The two sides look the key up in different columns -- an entity or a
        prefix -- and that is a judge's decision, not a query the base can
        build from a declared type.
        """
        parent = self.parent
        contact = parent.contact
        item = self._entity(contact.get("Call", ""))
        if item is None:
            contact["IsMultiplier1"] = 0
            return
        if self.my_country.upper() == item.get("entity", "").upper():
            contact["IsMultiplier1"] = 0
            return

        band = contact.get("Band")
        if self.my_continent == "AS":
            expression, value = "CountryPrefix", item.get("primary_pfx", "")
        else:
            if item.get("continent", "") != "AS":
                contact["IsMultiplier1"] = 0
                return
            expression = "WPXPrefix"
            value = calculate_wpx_prefix(contact.get("Call", ""))
        if not value:
            contact["IsMultiplier1"] = 0
            return
        result = parent.database.mult_key_exists(
            expression, value, ("Band",), band=band
        )
        contact["IsMultiplier1"] = 0 if result.get("count", 0) else 1

    def cabrillo_qso_line(self, contact):
        """The standard line, with the received age padded to two digits.

        The base's line ends with the received exchange padded to six columns;
        this replaces just that tail, so nothing else about the layout moves.
        """
        number = str(contact.get("NR", ""))
        line = super().cabrillo_qso_line(contact)
        return f"{line[: -len(number.ljust(6))]}{number.zfill(2).ljust(6)}"
