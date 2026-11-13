"""ES MANUAL KEY

Find rules at: https://erau.ee/images/LL/ES-Open_rules.pdf

A 45-minute CW contest worked in three 15-minute periods: a station may be
worked again in each new period.  A contact is worth the correspondent's
seniority -- the first two digits of the received exchange -- plus a bonus for
the less experienced: 20 points under 10 years, 10 between 11 and 20.  The
operator's own seniority, from the licence class, is added three times to the
total, and the multiplier is each Estonian call area (the third character of
the WPX prefix) once per band and mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase, period_dupe_check
from not1mm.lib.ham_utility import calculate_wpx_prefix


class Contest(ContestBase):
    """ES MANUAL KEY."""

    DisplayName = "ES MANUAL KEY"
    CabrilloName = "ES-MANUAL-KEY"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    DupeType = 5  # a call again in each 15-minute period
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
    # The reports, our licence class and serial and their seniority code.
    FrameText = ("", "Sent", "SN")
    AccessibleNames = ("", "", "Sent", "SN")
    # Each Estonian call area once per band and mode.
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 3

    def specific_contest_check_dupe(self, call: str) -> dict:
        """A call per band and mode in each 15-minute period of the 45 minutes."""
        return period_dupe_check(self.parent, call, 45, 15)

    def points(self):
        """The correspondent's seniority plus the low-experience bonus."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0
        if parent.contact.get("Mode", "").upper() not in (
            "CW",
            "CW-U",
            "CW-L",
            "CW-R",
            "CWR",
        ):
            return 0
        try:
            seniority = int(str(parent.contact.get("NR", "")).strip()[:2])
        except ValueError:
            seniority = 0
        if seniority < 10:
            return seniority + 20
        if 10 < seniority <= 20:
            return seniority + 10
        return seniority

    def mult_value(self, slot, contact):
        """The Estonian call area, from the third character of the prefix."""
        if slot == 1:
            if contact.get("CountryPrefix", "") != "ES":
                return None
            prefix = str(contact.get("WPXPrefix", "") or "")
            if not prefix:
                return None
            if prefix == calculate_wpx_prefix(self.parent.station.get("Call", "")):
                return None
            return prefix[2:3]
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            own = calculate_wpx_prefix(self.parent.station.get("Call", ""))
            return (
                "CASE WHEN CountryPrefix = 'ES' AND WPXPrefix <> "
                f"'{own}' THEN substr(WPXPrefix, 3, 1) END"
            )
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0

    def prefill(self):
        """The operator's licence class followed by the next serial."""
        parent = self.parent
        if parent.other_1.text():
            return
        setting = str(parent.contest_settings.get("SentExchange", "") or "").strip()
        if not setting:
            return
        if setting in ("#", "001"):
            exchange = (
                f"{parent.station.get('LicenseClass', '')}"
                f"{parent.process_macro('#', cut=False)}"
            )
        else:
            exchange = parent.process_macro(setting, cut=False)
        if exchange:
            parent.other_1.setText(exchange)

    def calc_score(self):
        """The QSO points plus the operator's own seniority, times multipliers."""
        parent = self.parent
        try:
            own = 3 * int(str(parent.station.get("LicenseClass", "")).strip()[:2])
        except ValueError:
            own = 3
        return (self.just_points() + own) * self.show_mults()

    def recalculate_mults(self):
        """Fill the call prefixes the multiplier and the ES filter read.

        An imported log carries neither for sure, so both are looked up from
        cty -- the pass the module made.  It marks no ``IsMultiplierN``: the
        column is not in this contest's log and the score counts from the log.
        """
        parent = self.parent
        for contact in parent.database.fetch_all_contacts_asc():
            result = parent.cty_lookup(contact.get("Call", ""))
            if result is None:
                continue
            item = result.get(next(iter(result)))
            contact["CountryPrefix"] = item.get("primary_pfx", "")
            contact["WPXPrefix"] = calculate_wpx_prefix(contact.get("Call", ""))
            parent.database.change_contact(contact)
