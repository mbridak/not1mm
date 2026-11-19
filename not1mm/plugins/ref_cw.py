"""French REF DX Contest (Coupe du REF), CW

Find rules at: https://concours.r-e-f.org/contest/a-propos/
Upload logs at: https://concours.r-e-f.org/contest/logs/upload-form/

80, 40, 20, 15 and 10m, once per band.  A French station sends RST and a
department (or its DOM/TOM prefix), everyone else RST and a serial number.  A
French entrant scores 6 points against another French station on the same
continent, 15 against one on another, 1 against a foreign station on the same
continent and 2 against one on another; a foreign entrant scores 1 against a
French station on its continent and 3 against one on another, and nothing for
any other contact.  The multipliers are the departments and DOM/TOM prefixes --
the exchange any French station sends -- and the non-French DXCC countries a
French entrant works, each once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


def _is_french(prefix) -> bool:
    """True for a French station: F itself or a DOM/TOM prefix (FG, FM, ...).

    Every primary prefix in cty.dat that starts with F is a French territory.
    """
    return bool(prefix) and str(prefix).upper().startswith("F")


class Contest(ContestBase):
    """French REF DX Contest, CW."""

    DisplayName = "French REF DX contest - CW"
    CabrilloName = "REF-CW"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Department or #"
    DupeType = 2  # 1 once per contest, 2 work each band, 3 each band/mode
    SendsRTCScore = True
    Bands = (3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]
    FrameText = ("", "Sent", "Dep/Pfx/SN")
    AccessibleNames = ("", "", "Sent", "Department, Prefix or SN")
    # The exchange a French station sends within the band, and the non-French
    # DXCC countries a French entrant works; each once per band.
    NumMults = 2
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1

    def _primary_pfx(self, call) -> str:
        """The primary prefix of a callsign, or "" when it is not in cty.dat."""
        result = self.parent.cty_lookup(call)
        if not result:
            return ""
        item = result.get(next(iter(result)), {})
        return item.get("primary_pfx", "")

    def _continent(self, call) -> str:
        """The continent of a callsign, or "" when it is not in cty.dat."""
        result = self.parent.cty_lookup(call)
        if not result:
            return ""
        item = result.get(next(iter(result)), {})
        return item.get("continent", "")

    def _i_am_french(self) -> bool:
        """Whether the operator is in France (or a DOM/TOM)."""
        return _is_french(self._primary_pfx(self.parent.station.get("Call", "")))

    @staticmethod
    def _stored_nr(value):
        """The received exchange in the form the log stores it.

        ``NR`` is an INTEGER column, so an all-digit department is stored as a
        number and a DOM/TOM prefix as text.  The live existence check compares
        the column's value with this key, and a text "75" would not equal the
        stored ``75`` once a ``CASE`` has stripped the column's affinity.
        """
        text = str(value or "").strip()
        if not text:
            return None
        return int(text) if text.isdigit() else text.upper()

    def points(self):
        """The QSO points: a two-sided ladder, so the rule is a method."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        my_continent = self._continent(parent.station.get("Call", ""))
        their_continent = self._continent(parent.contact.get("Call", ""))
        im_french = self._i_am_french()
        they_french = _is_french(self._primary_pfx(parent.contact.get("Call", "")))

        if im_french:
            if they_french:
                return 6 if my_continent == their_continent else 15
            return 1 if my_continent == their_continent else 2
        if they_french:
            return 1 if my_continent == their_continent else 3
        return 0

    def mult_sql(self, slot):
        """A department from a French station; a country only for a French log."""
        if slot == 1:
            return "CASE WHEN CountryPrefix LIKE 'F%' AND NR <> '' THEN NR END"
        if slot == 2:
            if not self._i_am_french():
                return None
            return (
                "CASE WHEN CountryPrefix <> '' AND CountryPrefix NOT LIKE 'F%' "
                "THEN CountryPrefix END"
            )
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same two keys in Python, for the log and the replay."""
        if slot == 1:
            if not _is_french(contact.get("CountryPrefix", "")):
                return None
            return self._stored_nr(contact.get("NR", ""))
        if slot == 2:
            prefix = contact.get("CountryPrefix", "")
            if not prefix or _is_french(prefix) or not self._i_am_french():
                return None
            return str(prefix).upper()
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The exchange; the received half is a department, a prefix or a serial."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()
        self.mark_multipliers()

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        if self.parent.log_window:
            self.parent.log_window.msg_from_main({"cmd": "UPDATELOG"})

    def populate_history_info_line(self):
        """Show history info if available."""
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
        """Prefill the received exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Exch1', '')}")
