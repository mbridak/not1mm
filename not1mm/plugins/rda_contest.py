"""Russian District Award (RDA) Contest plugin.

Status:            Active
Geographic Focus:  Russia
Participation:     Worldwide
Mode:              CW, SSB
Bands:             160, 80, 40, 20, 15, 10m (no WARC)
Classes:           Single Op All Band (EUR / ASR / World, MIX/CW/SSB, HP/LP)
                   Multi-Op All Band
                   Field (C1/C2, Russian only)
Exchange:          Russian stations: RS(T) + RDA district code (e.g. TB02)
                   non-Russian stations: RS(T) + Serial No. starting at 001
Work stations:     Once per band per mode (dupe)
QSO Points:
                   Russian stations:
                      1 pt QSO with Russia on your continent
                      2 pts QSO with Russia on another continent
                      3 pts QSO with a different country on your continent
                     10 pts QSO with a DX entity from the official C1/C2 list
                      5 pts QSO with another continent
                   Non-Russian stations:
                     10 pts QSO with a Russian station
                   Kaliningrad (R2F/UA2) is a separate DXCC entity, but points
                   for QSOs with Kaliningrad are counted as for European Russia.
Multipliers:       Russian stations: each DXCC country once + each RDA district once
                   Non-Russian stations: each RDA district once
Score Calculation: Total score = total QSO points x total multipliers
Find rules at:     https://www.rdaward.org/rdac.htm (RDA CONTEST)
Cabrillo name:     RDAC
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

logger = logging.getLogger(__name__)

# Primary prefixes assigned to Russian stations by the country file.
# UA = European Russia, UA9 = Asiatic Russia, UA2 = Kaliningrad.
RUSSIA_PREFIXES = ("UA", "UA9", "UA2")

# Entity names used by the country file (cty.json / CTY).
RUSSIA_ENTITIES = ("European Russia", "Asiatic Russia", "Kaliningrad")

# Official C1/C2 list of rare DX entities that earn 10 points for a cross
# continent QSO from a Russian station.  Populate this set from the current
# year's rules; the values change from year to year.
SPECIAL_DX = {
    # "Vatican",
    # "Banaba Island",
}

# The Russian prefixes as a SQL list, for the district key.
RUSSIA_PREFIX_LIST = ", ".join(f"'{prefix}'" for prefix in RUSSIA_PREFIXES)


def is_russian_prefix(prefix: str) -> bool:
    """Return True if the country prefix belongs to a Russian station."""
    return prefix.upper() in RUSSIA_PREFIXES


def country_mult_prefix(prefix: str) -> str:
    """Return a single grouping key for DXCC country multipliers.

    European Russia (UA) and Asiatic Russia (UA9) are two DXCC entities, as
    is Kaliningrad (UA2), so each counts as its own country multiplier.  Only
    the *points* for a Kaliningrad QSO are counted as for European Russia
    (rule 9.3); they used to share one multiplier with European Russia.
    """
    return prefix.upper()


def is_maritime_mobile(call: str) -> bool:
    """Return whether a callsign ends with the maritime-mobile suffix."""
    return call.strip().upper().endswith("/MM")


def my_station_is_russian(parent) -> bool:
    """Return True if the operating station is located in Russia."""
    result = parent.cty_lookup(parent.station.get("Call", ""))
    if result is None:
        return False
    item = result.get(next(iter(result)))
    return item.get("entity", "") in RUSSIA_ENTITIES


class Contest(ContestBase):
    """Russian District Award Contest."""

    DisplayName = "RDA Contest"
    CabrilloName = "RDAC"
    Mode = "BOTH"
    EXCHANGE_HINT = "# or RDA code"
    SOAPBOX_HINT = (
        "RDA Contest - Exchange: RS(T) + serial (non-RU) or RDA district code (RU)"
    )
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SendsRTCScore = True
    # The reports, our exchange (a district code from Russia, else a serial)
    # and the received one.
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    QsoErrorString = "SntNrText_Any_not_Empty, RcvNrText_Any_not_Empty"
    FrameText = ("SNT", "RCV", "SentNR", "Serial or RDA")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Serial Number or Russian RDA district",
    )
    # Each Russian station's district once for the contest, and -- from a
    # Russian station -- each DXCC country once per band.
    NumMults = 2
    Multiplier1Name = "State"
    MultSqlString = "NR"
    IsMult1Per = 4
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "M1",
        "M2",
        "PTS",
    ]

    def am_russian(self) -> bool:
        """True when the entrant is a Russian station."""
        return my_station_is_russian(self.parent)

    def his_prefix(self, contact) -> str:
        """The worked station's prefix, from the contact or from cty."""
        countryprefix = contact.get("CountryPrefix", "")
        if not countryprefix:
            result = self.parent.cty_lookup(contact.get("Call", ""))
            if result:
                item = result.get(next(iter(result)))
                countryprefix = item.get("primary_pfx", "")
        return countryprefix

    def my_sent_exchange(self) -> str:
        """The exchange this station transmits.

        Russian stations send their fixed RDA district code, configured in the
        contest "Sent Exchange" field.  Non-Russian stations send a running
        serial number instead.
        """
        parent = self.parent
        if self.am_russian():
            rda = str(parent.contest_settings.get("SentExchange", "")).strip()
            if rda:
                return rda.upper()
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        return serial_nr

    def prefill(self):
        """Fill our half of the exchange: a district code or the next serial."""
        if len(self.parent.fields.SntNrText.text()) == 0:
            self.parent.fields.SntNrText.setText(self.my_sent_exchange())

    def set_contact_vars(self):
        """The reports, our exchange, and the received district or serial."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        # The operator may have edited the sent box after prefill; fall back
        # to the computed exchange when it is empty.
        parent.contact["SentNr"] = (
            parent.fields.SntNrText.text() or self.my_sent_exchange()
        )
        parent.contact["NR"] = parent.fields.RcvNrText.text().upper()
        parent.contact["IsMultiplier1"] = 0
        parent.contact["IsMultiplier2"] = 0
        if parent.contact_is_dupe == 0:
            self.mark_multipliers()

    def mult_value(self, slot, contact):
        """The district from a Russian station, the country from a Russian entrant."""
        if slot == 1:
            if not is_russian_prefix(self.his_prefix(contact) or ""):
                return None
            return contact.get("NR") or None
        if slot == 2:
            if not self.am_russian():
                return None
            if is_maritime_mobile(contact.get("Call", "")):
                return None
            return self.his_prefix(contact) or None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same two keys as SQL, for counting the log."""
        if slot == 1:
            return (
                "CASE WHEN CountryPrefix IN "
                f"({RUSSIA_PREFIX_LIST}) AND NR <> '' THEN NR END"
            )
        if slot == 2:
            if not self.am_russian():
                return None
            return "CASE WHEN Call NOT LIKE '%/MM%' THEN CountryPrefix END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's two rows, under the names this contest used."""
        return {"country": self._mult_count(2), "rda": self._mult_count(1)}

    def points(self):
        """The Russian/foreign ladder; a non-Russian to non-Russian QSO is nothing."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        call = parent.contact.get("Call", "")

        mycountry = ""
        mycontinent = ""
        hiscountry = ""
        hiscontinent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            mycountry = item.get("entity", "")
            mycontinent = item.get("continent", "")

        result = parent.cty_lookup(call)
        if result is not None:
            item = result.get(next(iter(result)))
            hiscountry = item.get("entity", "")
            hiscontinent = item.get("continent", "")

        if not hiscountry:
            return 0

        his_is_russian = hiscountry in RUSSIA_ENTITIES
        my_is_russian = mycountry in RUSSIA_ENTITIES

        if my_is_russian:
            # Russian station
            if his_is_russian:
                if mycontinent == hiscontinent:
                    return 1  # QSO with Russia on your continent
                return 2  # QSO with Russia on another continent
            if mycontinent == hiscontinent:
                return 3  # QSO with a different country on your continent
            if hiscountry in SPECIAL_DX:
                return 10  # QSO with a DX entity from the C1/C2 list
            return 5  # QSO with another continent

        # Non-Russian station
        if his_is_russian:
            return 10  # QSO with Russian station
        return 0

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
        """Prefill the received district from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.RcvNrText.text() == "":
                parent.fields.RcvNrText.setText(f"{result.get('Exch1', '')}")
