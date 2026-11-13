"""Oceania DX Contest, CW

Find rules at: https://www.oceaniadxcontest.com/

160-10m, once per band.  The band sets the points -- 20 for 160m, 10 for 80m,
5 for 40m, 1 for 20m, 2 for 15m and 3 for 10m -- but only a contact with one
end in Oceania scores at all.  Each different prefix worked counts once per
band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# The band, in MHz, and what a contact on it is worth.
BAND_POINTS = {
    1.8: 20,
    3.5: 10,
    7.0: 5,
    14.0: 1,
    21.0: 2,
    28.0: 3,
}

BAND_LIST = ", ".join(str(band) for band in BAND_POINTS)


def _band_key(band) -> float:
    """Return the band as the float the point table is keyed on.

    Band arrives from the radio as "14.0" and comes back from the database as
    the float 14.0, and a string is not a key here.
    """
    try:
        return float(band)
    except (TypeError, ValueError):
        return 0.0


class Contest(ContestBase):
    """Oceania DX Contest, CW."""

    DisplayName = "Oceania DX CW"
    CabrilloName = "OCEANIA-DX-CW"
    Mode = "CW"
    EXCHANGE_HINT = "#"
    DefaultContestExchange = "#"  # a serial number
    DupeType = 2  # the same station may only be counted once on each band
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
    # Each prefix once per band, but only while one end is in Oceania.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 1
    SendsRTCScore = True
    # Which side of the contest we are on, worked out in init_contest.
    my_continent = ""

    def init_contest(self):
        """Set up the entry window, then work out where the operator is."""
        super().init_contest()
        result = self.parent.cty_lookup(self.parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            self.my_continent = item.get("continent", "")

    def _in_oceania(self, contact) -> bool:
        """True when either end of the contact is in Oceania."""
        return self.my_continent == "OC" or contact.get("Continent", "") == "OC"

    def points(self):
        """The band's points, when one end of the contact is in Oceania."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        if not self._in_oceania(parent.contact):
            return 0
        return BAND_POINTS.get(_band_key(parent.contact.get("Band", 0.0)), 0)

    def mult_value(self, slot, contact):
        """The prefix, once per band, while one end is in Oceania."""
        if slot != 1:
            return super().mult_value(slot, contact)
        if _band_key(contact.get("Band")) not in BAND_POINTS:
            return None
        if not self._in_oceania(contact):
            return None
        return contact.get("WPXPrefix") or None

    def mult_sql(self, slot):
        """The same prefix key as SQL, for counting the log."""
        if slot != 1:
            return super().mult_sql(slot)
        conditions = [f"Band IN ({BAND_LIST})", "WPXPrefix <> ''"]
        if self.my_continent != "OC":
            conditions.append("Continent = 'OC'")
        return "CASE WHEN " + " AND ".join(conditions) + " THEN WPXPrefix END"

    def cabrillo_qso_line(self, contact):
        """The base's line, with the received serial padded to two digits."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).zfill(2).ljust(6)}"
        )
