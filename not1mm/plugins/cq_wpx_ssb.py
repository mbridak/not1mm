"""CQ WPX SSB plugin.

Find rules at: https://www.cqwpx.com/rules.htm

Presented by CQ Magazine, 0000 UTC Saturday to 2359 UTC Sunday in March.
    Bands:      160, 80, 40, 20, 15, 10m
    Exchange:   RS + serial number
    Work:       once per band
    QSO points: 6 per 160/80/40m contact with another continent,
                3 per 20/15/10m contact with another continent,
                1 for the same country,
                and for the same continent but another country it is 4 on
                the low bands and 2 on the high ones if you are in North
                America, otherwise 2 and 1.
    Multipliers: prefixes, counted once for the whole contest
    Cabrillo:   CQ-WPX-SSB

The same contest as :mod:`not1mm.plugins.cq_wpx_cw`, in phone, which is why
the two classes are nearly identical; a per-family base class will absorb the
scoring they share.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """CQ WPX, SSB."""

    DisplayName = "CQ WPX SSB"
    CabrilloName = "CQ-WPX-SSB"
    Mode = "SSB"
    EXCHANGE_HINT = "#"
    DefaultContestExchange = "#"  # a serial number
    ADIFContestID = "CQ-WPX-SSB"
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "WPX",
        "M1",
        "PTS",
    ]
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 4  # a prefix counts once for the whole contest

    def points(self):
        """Points for the contact being logged.

        Depends on the two continents and, within a continent, on the band.
        UDC's PointsPerContact has no way to say "if I am in North America",
        so this stays a method.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_country = item.get("entity", "")
            my_continent = item.get("continent", "")
        result = parent.cty_lookup(parent.contact.get("Call", ""))
        band = int(int(float(parent.contact.get("Freq", 0))) / 1000)
        if result is not None:
            item = result.get(next(iter(result)))
            their_country = item.get("entity", "")
            their_continent = item.get("continent", "")

            if my_continent != their_continent:
                if band in [28, 21, 14]:
                    return 3
                return 6

            if my_country.upper() == their_country.upper():
                return 1

            if my_continent == "NA":
                if band in [28, 21, 14]:
                    return 2
                return 4

            if band in [28, 21, 14]:
                return 1
            return 2
        # Something wrong
        return 0
