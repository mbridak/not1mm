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
    PointsRules = "SSB, 1, FM, 1, AM, 1, RTTY, 2, CW, 3"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "Automobile Code"
    Bands = (3.5, 7)
    # The whole exchange is the automobile code, in Exchange1Text.
    EntryWindowInfo = ("SNTText", 450, "RCVText", 450, "Exchange1Text", 615)
    FrameText = ("SNT", "RCV", "Automobile Code")
    AccessibleNames = (
        "RST Sent",
        "RST Received",
        "Received Exchange",
    )
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

    def set_contact_vars(self):
        """The exchange, and the automobile code the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        parent.contact["NR"] = parent.fields.Exchange1Text.text().upper()
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
            if parent.fields.Exchange1Text.text() == "":
                parent.fields.Exchange1Text.setText(f"{result.get('Sect', '')}")
