"""Ernst Krenkel Memorial Contest (RAEM)

Find rules at: https://raem.srr.ru/rules/

80m through 10m, CW only, once per band.  The exchange is a serial number and
the station's latitude and longitude in whole degrees with a hemisphere letter
(N/S and W/O for east), e.g. "57N85O".

A contact is 50 points plus one for every degree of latitude difference and
again for longitude, 100 more when the other station is inside the polar
circles and 300 more for the RAEM memorial station itself.  An entrant inside
the polar circles multiplies the total by 1.1.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import logging
import re

from not1mm.lib.contest import ContestBase

logger = logging.getLogger(__name__)

# The latitude and longitude, each with its hemisphere letter.
_RAEM_COORDS = re.compile(r"(\d+)([NS])(\d+)([WO])")


def _latlon(exchange) -> tuple | None:
    """Return the (latitude, longitude) of a RAEM exchange, or None.

    The exchange is the latitude with S or N and then the longitude with W or
    O (east), e.g. "57N85O"; the letter gives the sign - N and O positive, S
    and W negative.  A leading serial number is ignored.
    """
    match = _RAEM_COORDS.search(str(exchange).upper())
    if match is None:
        return None
    latitude = int(match.group(1)) * (1 if match.group(2) == "N" else -1)
    longitude = int(match.group(3)) * (1 if match.group(4) == "O" else -1)
    return latitude, longitude


def latlondif(parent, exchange1) -> tuple:
    """Return the (coordinate points, the other station is polar) for a QSO.

    Rule 5: one point for every degree of latitude difference and again for
    longitude, and 100 more when the other station is inside the polar
    circles.  The hemisphere letters set the sign, so a station at 117 west
    and one at 37 east are 154 degrees apart, not 80.
    """
    ours = _latlon(parent.contest_settings.get("SentExchange", ""))
    theirs = _latlon(exchange1)
    if ours is None or theirs is None:
        return 0, False
    ourlat, ourlon = ours
    hislat, hislon = theirs
    dlat = abs(ourlat - hislat)
    dlon = abs(ourlon - hislon)
    if dlon > 180:
        # The other way round is shorter: 117 west to 85 east is 158 degrees.
        dlon = 360 - dlon
    return dlat + dlon, abs(hislat) >= 66


class Contest(ContestBase):
    """Ernst Krenkel Memorial Contest."""

    DisplayName = "RAEM"
    CabrilloName = "RAEM"
    Mode = "CW"
    EXCHANGE_HINT = "33N117W"
    SOAPBOX_HINT = """
In the exchange field put just your Lat and Lon. for me 33N117W.
And in the exchange macro put '# {EXCH}'.
"""
    DupeType = 2  # once per band
    Bands = (3.5, 7, 14, 21, 28)
    SendsRTCScore = True
    # The received RST is hidden: the entry window is our serial, their serial
    # and their coordinates.
    EntryWindowInfo = ("SntNrText", 625, "RcvNrText", 625, "Exchange1Text", 615)
    FrameText = ("Sent S/N", "Rcv S/N", "Exchange")
    AccessibleNames = ("Sent Serial Number", "Serial Number", "Exchange")
    QsoErrorString = "RcvNrText_Any_not_Empty, Exchange1Text_Any_not_Empty"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "PTS",
    ]

    def interface(self):
        """The entry window, and a blank sent-serial field."""
        super().interface()
        self.parent.fields.SntNrText.setText("")

    def prefill(self):
        """Fill the sent serial, which lives in the sent field here."""
        serial_nr = str(self.parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.parent.fields.SntNrText.text()) == 0:
            self.parent.fields.SntNrText.setText(serial_nr)

    def set_contact_vars(self):
        """The reports are fixed; the serials and the coordinates are typed."""
        parent = self.parent
        parent.contact["SNT"] = "599"
        parent.contact["RCV"] = "599"
        parent.contact["SentNr"] = parent.fields.SntNrText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text()
        parent.contact["Exchange1"] = parent.fields.Exchange1Text.text()

    def points(self):
        """50 points, the degrees apart, and the two bonuses."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        points = 50
        morepoints, ispolar = latlondif(parent, parent.contact.get("Exchange1", ""))
        points += morepoints
        if ispolar:
            points += 100
        if str(parent.contact.get("Call", "")).upper() == "RAEM":
            points += 300
        return points

    def show_mults(self):
        """A polar entrant's score multiplier: 1.1 inside the circles, else 1."""
        ours = _latlon(self.parent.contest_settings.get("SentExchange", ""))
        if ours is not None and abs(ours[0]) >= 66:
            return 1.1
        return 1

    def calc_score(self):
        """The points times that multiplier, as a whole number."""
        result = self.parent.database.fetch_points()
        points = 0
        if result is not None:
            points = int(result.get("Points") or 0)
        return round(points * self.show_mults())

    def recalculate_mults(self):
        """Nothing to mark: there is no counted multiplier, only the 1.1."""

    def cabrillo_qso_line(self, contact):
        """The RAEM line: the serial and the coordinates both ways."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).ljust(6)} "
            f"{self.parent.contest_settings.get('SentExchange', '').ljust(14).upper()}"
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(6)}"
            f"{str(contact.get('Exchange1', '')).ljust(14)} "
        )

    def populate_history_info_line(self):
        """Show what call history knows about the station."""
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
        """Prefill the coordinates from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.Exchange1Text.text() == "":
                parent.fields.Exchange1Text.setText(f"{result.get('Exch1', '')}")
