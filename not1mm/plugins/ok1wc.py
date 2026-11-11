"""OK1WC Memorial Contest (MWC) plugin.

Find rules at: https://memorial-ok1wc.cz/index.php?page=deniky

One hour every Monday 16:30 UTC, CW-only, 40m/80m, serial exchange.  One point
a QSO; the multiplier is the last character of the callsign, once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """OK1WC Memorial Contest (MWC)."""

    DisplayName = "OK1WC Memorial Contest (MWC)"
    CabrilloName = "MWC"
    Mode = "CW"
    EXCHANGE_HINT = "#"
    DefaultContestExchange = "#"  # a serial number
    ADIFContestID = "MWC"
    SendsRTCScore = True
    Bands = (3.5, 7)
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
    PointsPerContact = 1
    NumMults = 1
    Multiplier1Name = "Callsign"
    MultSqlString = "LASTLETTER"
    IsMult1Per = 1  # the last letter counts once per band
