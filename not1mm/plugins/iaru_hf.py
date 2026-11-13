"""
IARU HF World Championship  IARU-HF

Exchange:       IARU HQ: RS(T) + IARU Society
                Non-HQ: RS(T) + ITU Zone No.

Work stations:  Once per band per mode

QSO Points:     1 point per QSO with same zone or with HQ stations
                3 points per QSO with different zone on same continent
                5 points per QSO with different zone on different continent

Multipliers:    Each ITU zone once per band
                Each IARU HQ and each IARU official once per band

Find rules at: https://contests.arrl.org/ContestRules/IARU-HF-Rules.pdf
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """IARU HF World Championship."""

    DisplayName = "IARU HF"
    CabrilloName = "IARU-HF"
    Mode = "BOTH"
    EXCHANGE_HINT = "ITU Zone"
    ZoneType = "IARU"  # the exchange is the ITU zone
    DupeType = 3  # once per band per mode
    SendsRTCScore = True
    # Only the RSTs and the received zone/society are used; the sent exchange
    # is the fixed station setting, so the first extra field stays hidden.
    EntryFields = ("field1", "field2", "field4")
    FrameText = ("SNT", "", "ITU Zone")
    AccessibleNames = ("RST Sent", "", "", "I T U Zone")
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
    # Each ITU zone and each HQ society/official once per band -- not once per
    # mode (rule 5.2.1).
    NumMults = 2
    Multiplier1Name = "ITUZone"
    MultSqlString = "CQZONE"
    IsMult1Per = 1
    Multiplier2Name = "HQ"
    MultSqlString2 = "IARUZONE"
    IsMult2Per = 1

    def mult_value(self, slot, contact):
        """A zone number for slot 1, a society abbreviation for slot 2.

        The received exchange is both: ``ZN`` is an INTEGER column, so a zone
        is stored as a number and an HQ station's society stays text.
        """
        zone = contact.get("ZN")
        if zone is None:
            return None
        value = str(zone).strip()
        if slot == 1:
            return value if value.isdigit() else None
        if slot == 2:
            return value if value and not value.isdigit() else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """Split the one column into a zone key and an HQ key."""
        if slot == 1:
            return "CASE WHEN typeof(ZN) = 'integer' THEN ZN END"
        if slot == 2:
            return "CASE WHEN typeof(ZN) != 'integer' AND ZN <> '' THEN ZN END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's two rows, under the names this contest used."""
        return {"state": self._mult_count(2), "zone": self._mult_count(1)}

    def set_contact_vars(self):
        """Contest Specific"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["ZN"] = parent.other_2.text()
        parent.contact["NR"] = parent.other_2.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)

    def prefill(self):
        """Fill ITU Zone"""
        parent = self.parent
        if len(parent.other_2.text()) == 0:
            parent.other_2.setText(str(parent.contact.get("ZN", "")))
        parent.other_1.setText(str(parent.contest_settings.get("SentExchange", 0)))

    def points(self):
        """
        QSO Points: 1 point per QSO with same zone or with HQ stations
                    3 points per QSO with different zone on same continent
                    5 points per QSO with different zone on different continent
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        result = parent.cty_lookup(parent.station.get("Call", ""))
        mycontinent = ""
        if result is not None:
            item = result.get(next(iter(result)))
            mycontinent = item.get("continent", "")

        try:
            our_itu = int(str(parent.station.get("IARUZone", 0) or 0).strip())
        except ValueError:
            our_itu = 0

        try:
            their_itu = int(str(parent.contact.get("ZN", "")).strip())
        except ValueError:
            # An IARU member-society HQ station or official sends a society
            # abbreviation instead of a zone: one point (rule 5.1.2).
            return 1

        if our_itu == their_itu:
            return 1

        # The continent is normally in the contact, but an imported log need
        # not carry a CONTINENT field - fall back to the country file.
        hiscontinent = parent.contact.get("Continent", "")
        if not hiscontinent:
            result = parent.cty_lookup(parent.contact.get("Call", ""))
            if result is not None:
                item = result.get(next(iter(result)))
                hiscontinent = item.get("continent", "")

        if hiscontinent == mycontinent:
            return 3
        return 5

    def recalculate_mults(self):
        """Mark nothing, as the module did.

        The module never wrote ``IsMultiplierN``: the zones and the HQ
        societies are counted from the log, and the M column is not in
        :attr:`LogInfo`.  The base would otherwise start marking rows.
        """

    def populate_history_info_line(self):
        """Show what call history knows about the station."""
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
        """Prefill the received ITU zone from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
