"""DARC Christmas Contest (XMAS)

Find rules at: https://www.darc.de/der-club/referate/conteste/weihnachtswettbewerb/regeln/
Upload logs at: https://dxhf2.darc.de/~xmaslog/upload.cgi?form=referat&lang=de

80m and 40m, once per band and mode.  The exchange is RST and a DOK, or "NM"
for a non-member in DL and a serial number from outside.  Each DOK and each
WPX prefix is a multiplier once per band and mode; "NM" and an empty prefix
are not multipliers.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW


class Contest(ContestBase):
    """DARC Christmas Contest."""

    DisplayName = "DARC XMAS"
    CabrilloName = "XMAS"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "DOK/NM or #"
    DupeType = 3  # work each band/mode once
    SendsRTCScore = True
    PointsPerContact = 1
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "DOK/# Sent", "DOK/# RCVD")
    AccessibleNames = ("RST Sent", "RST Received", "Sent DOK", "DOK/NM or Number")
    # A WPX prefix and a DOK, each once per band and mode.
    NumMults = 2
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 3
    Multiplier2Name = "DOK"
    MultSqlString2 = "NR"
    IsMult2Per = 3

    def mult_sql(self, slot):
        """A prefix is not a multiplier when empty; a DOK only from DL.

        A DOK counts only for a DL station, only when it is text (a serial from
        outside is not a district) and only when it is not "NM"; an empty value
        is not one either.  The module's replay said the same, and its query
        compared the stored ``NR``.
        """
        if slot == 1:
            return "NULLIF(WPXPrefix, '')"
        if slot == 2:
            return (
                "CASE WHEN CountryPrefix = 'DL' AND typeof(NR) = 'text' "
                "AND NR <> '' AND upper(NR) <> 'NM' THEN upper(NR) END"
            )
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same key as :meth:`mult_sql`, from a contact."""
        if slot == 1:
            return contact.get("WPXPrefix") or None
        if slot == 2:
            dok = contact.get("NR", "")
            if (
                contact.get("CountryPrefix") == "DL"
                and isinstance(dok, str)
                and dok
                and dok.upper() != "NM"
            ):
                return dok.upper()
            return None
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The received DOK, and the two multipliers it is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()
        self.mark_multipliers()

    def prefill(self):
        """Fill the sent exchange, then recall the station's last DOK."""
        parent = self.parent
        super().prefill()
        if parent.fields.RcvNrText.text():
            return
        call = parent.callsign.text().upper()
        result = parent.database.exec_sql(
            "select NR from dxlog where Call = ? and ContestName = ? "
            "order by ts desc;",
            (call, self.CabrilloName),
        )
        if result and isinstance(result.get("NR", ""), str):
            parent.fields.RcvNrText.setText(str(result.get("NR", "")))

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Exch1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received DOK from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Exch1', '')}")
