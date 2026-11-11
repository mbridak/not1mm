"""ARI 40/80 plugin

Find rules at: https://www.ari.it/en/contest-hf/contest-4080.html

40 and 80 metres, once per band and mode.  Both stations send an automobile
code, and the contact is worth 3 points on CW, 2 on RTTY and 1 on phone.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """ARI 40/80 metres."""

    DisplayName = "ARI 40 80"
    CabrilloName = "40-80"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "Automobile Code"
    ADIFContestID = "40-80"
    advance_on_space = [True, True, True, True, True]
    Bands = (3.5, 7)
    # The whole exchange is the automobile code, so other_1 is not used.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "Automobile Code")
    AccessibleNames = ("RST Sent", "", "", "Received Exchange")
    TabOrder = ("callsign", "sent", "receive", "other_2")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "RcvNr",
        "PTS",
    ]
    # The received automobile code, once per band and mode.
    NumMults = 1
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 3

    def mult_sql(self, slot):
        """The automobile code counts only when one was actually received."""
        if slot == 1:
            return "NULLIF(NR, '')"
        return super().mult_sql(slot)

    def points(self):
        """Points for the contact being logged: 3 CW, 2 RTTY, 1 phone."""
        if self.parent.contact_is_dupe > 0:
            return 0
        mode = self.parent.contact.get("Mode", "").upper()
        if mode in ("SSB", "USB", "LSB", "FM", "AM", "PH"):
            return 1
        if mode in ("RTTY", "RY"):
            return 2
        if mode in ("CW", "CW-U", "CW-L", "CW-R", "CWR"):
            return 3
        return 0

    def set_contact_vars(self):
        """The exchange, and the automobile code the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        parent.contact["NR"] = parent.other_2.text().upper()
        self.mark_multipliers()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Sect', '')}"
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
                parent.other_2.setText(f"{result.get('Sect', '')}")
