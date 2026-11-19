"""Stew Perry Topband Distance Challenge

Find rules at: https://www.kkn.net/stew/

160m only, CW, once per contest.  The exchange is a four character grid
square.  A contact is one point plus one more for every 500 km between the two
grids, and the entrant's own power multiplies the final score: 1.5x for low
power and 3x for QRP.  There are no multipliers.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import distance


class Contest(ContestBase):
    """Stew Perry Topband Distance Challenge."""

    DisplayName = "Stew Perry Topband"
    CabrilloName = "STEW-PERRY"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "4-Character grid square"
    DupeType = 1  # 1 once per contest, 2 work each band, 3 each band/mode
    SendsRTCScore = True
    Bands = (1.8,)
    # The grid is the only exchange field; other_2 is hidden.
    EntryFields = ("field1", "field2", "field3")
    FrameText = ("SNT", "Grid", "")
    AccessibleNames = ("RST Sent", "", "Grid", "")
    ESMExchangeField = "other_1"
    # After a call lookup the focus goes straight to the grid.
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "RcvNr",
        "PTS",
    ]

    def points(self):
        """Rule 5: one point a QSO plus one for every 500 km between the grids.

        The 2x for working a low-power station and the 4x for a QRP one are
        worked out by the contest's log checker from the other station's log,
        and the entrant's own power multiplies the final score (rule 7), so
        neither belongs on the contact.  The distance is read from the logged
        contact, not the entry field, which an imported log leaves empty.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        their_grid = str(parent.contact.get("NR", "")).upper()
        kilometers = distance(parent.station.get("GridSquare", ""), their_grid)
        return 1 + int(kilometers / 500)

    def calc_score(self):
        """Rule 7: the entrant's power multiplies the final score."""
        points = super().calc_score()
        power = str(self.parent.contest_settings.get("PowerCategory", "")).upper()
        if power == "QRP":
            return round(points * 3)
        if power == "LOW":
            return round(points * 1.5)
        return points

    def set_contact_vars(self):
        """The reports and the received grid; nothing is marked."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_1.text().upper()

    def prefill(self):
        """The operator types the grid; the setup has nothing to fill in."""

    def recalculate_mults(self):
        """There are no multipliers to mark."""

    def cabrillo_qso_line(self, contact):
        """The grid takes the serial's place, and there is no second field."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{self.parent.contest_settings.get('SentExchange', '').ljust(9).upper()}"
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).ljust(3)} "
            f"{str(contact.get('Sect', '')).ljust(6)}"
        )

    def populate_history_info_line(self):
        """Show the call history file's entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Loc1', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the grid from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Loc1', '')}")
