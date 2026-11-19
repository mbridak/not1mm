"""ES FIELD DAY

Find rules at: https://erau.ee/images/LL/ES-Open_rules.pdf

A two-hour contest worked in four 30-minute periods: a station may be worked
again in each new period.  Every contact is 1 point, 3 for a ``/P`` station and
5 for a ``/QRP`` one, and each Estonian region -- sent as the last two letters
of the received exchange -- counts once per band and mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase, period_dupe_check
from not1mm.lib.ham_utility import calculate_wpx_prefix

# The sixteen Estonian regions the received exchange may end with.
ESTONIAN_REGIONS = (
    "HM",
    "HR",
    "IV",
    "JG",
    "JR",
    "LN",
    "LV",
    "PL",
    "PU",
    "RP",
    "SR",
    "TA",
    "TL",
    "VC",
    "VO",
    "VP",
)

REGION_LIST = ",".join(f"'{region}'" for region in ESTONIAN_REGIONS)


class Contest(ContestBase):
    """ES Field Day."""

    DisplayName = "ES FIELD DAY"
    CabrilloName = "ES-FIELD-DAY"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    DupeType = 5  # a call again in each 30-minute period
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
    # The reports, our serial and their serial with the region code after it.
    FrameText = ("", "Sent", "SN")
    AccessibleNames = ("", "", "Sent", "SN")
    # Each region once per band and mode.
    NumMults = 1
    Multiplier1Name = "Sect"
    MultSqlString = "Sect"
    IsMult1Per = 3

    def specific_contest_check_dupe(self, call: str) -> dict:
        """A call per band and mode in each 30-minute period of the 2 hours."""
        return period_dupe_check(self.parent, call, 120, 30)

    def points(self):
        """One point a contact, three for /P and five for /QRP."""
        if self.parent.contact_is_dupe:
            return 0
        call = self.parent.contact.get("Call", "").lower()
        if "/p" in call:
            return 3
        if "/qrp" in call:
            return 5
        return 1

    def mult_value(self, slot, contact):
        """The region code at the end of an Estonian station's exchange."""
        if slot == 1:
            if contact.get("CountryPrefix", "") != "ES":
                return None
            exchange = str(contact.get("NR", "") or "")
            if not any("A" <= char <= "Z" for char in exchange):
                return None
            region = exchange[-2:]
            return region if region in ESTONIAN_REGIONS else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN CountryPrefix = 'ES' AND NR GLOB '*[A-Z]*' "
                f"AND substr(NR, -2) IN ({REGION_LIST}) "
                "THEN substr(NR, -2) END"
            )
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the serial-with-region exchange; nothing is marked."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text().upper()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0

    def prefill(self):
        """The next serial followed by the operator's region."""
        parent = self.parent
        if parent.other_1.text():
            return
        setting = str(parent.contest_settings.get("SentExchange", "") or "").strip()
        if not setting:
            return
        exchange = parent.process_macro(setting, cut=False)
        if setting in ("#", "001"):
            exchange = f"{exchange} {parent.station.get('State', '')}".strip()
        if exchange:
            parent.other_1.setText(exchange)

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
