"""European HF Championship (EUHFC)

Find rules at: https://euhf.s5cc.eu/

160-10m, once per band and mode.  The exchange is the operator's two-digit
licence year.  Only a contact with a continental-European station scores, one
point, and each different licence year counts once per band regardless of
mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """European HF Championship."""

    DisplayName = "EUHFC"
    CabrilloName = "EUHFC"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Lic. Year (2 digits)"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    # The hidden serial and the visible licence year.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "Lic Year")
    AccessibleNames = ("RST Sent", "", "", "License Year")
    # Each licence year once per band, whatever the mode.
    NumMults = 1
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    SendsRTCScore = True

    def points(self):
        """One point, and only for a continental-European contact."""
        if self.parent.contact_is_dupe:
            return 0
        if self.parent.contact.get("Continent", "") != "EU":
            return 0
        return 1

    def mult_value(self, slot, contact):
        """The licence year, unless the exchange is empty."""
        if slot == 1:
            year = contact.get("NR")
            return None if year in (None, "") else year
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL: an empty licence year is not a multiplier."""
        if slot == 1:
            return "NULLIF(NR, '')"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's single row, with the id the module used."""
        return {"licyear": self.show_mults()}

    def set_contact_vars(self):
        """The reports and the licence year; nothing is marked."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", "")

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""

    def cabrillo_qso_line(self, contact):
        """The licence years are two digits, so they get three columns."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).ljust(3)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).ljust(3)}"
        )

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Sect', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the licence year from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
