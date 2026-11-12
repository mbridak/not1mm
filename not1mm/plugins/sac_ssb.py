"""SAC SSB plugin

Find rules at: https://www.sactest.net/blog/scandinavian-activity-contest-2026-rules/
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of

# cty.dat's primary_pfx for each Scandinavian DXCC entity, which is what the
# log stores in CountryPrefix. The rules list the call areas in their own
# notation (OF0, OG0, OH0, OJ0, 5P, 7S, SA-SL ...), but none of those are ever
# the primary_pfx of a Scandinavian log entry, so matching on them missed
# Aland (OH0) and Market Reef (OJ0) altogether.
scandinavian_prefixes = [
    "JW",  # Svalbard
    "JX",  # Jan Mayen
    "LA",  # Norway
    "OH",  # Finland
    "OH0",  # Aland Islands
    "OJ0",  # Market Reef
    "OX",  # Greenland
    "OY",  # Faroe Islands
    "OZ",  # Denmark
    "SM",  # Sweden
    "TF",  # Iceland
]


def scandinavian_entity(contact) -> str:
    """The Scandinavian DXCC entity a contact belongs to, or "".

    cty.dat gives Bear Island, which is not a DXCC entity, its own record keyed
    "JW/b"; SAC section 2 counts it as part of Svalbard.
    """
    prefix = str(contact.get("CountryPrefix", ""))
    if prefix == "JW/b":
        return "JW"
    return prefix if prefix in scandinavian_prefixes else ""


class Contest(ContestBase):
    """Scandinavian Activity Contest, SSB."""

    DisplayName = "SAC SSB"
    CabrilloName = "SAC-SSB"
    Mode = "SSB"
    EXCHANGE_HINT = "#"
    DupeType = 2  # once per band
    Bands = (3.5, 7, 14, 21, 28)
    SendsRTCScore = True
    DefaultContestExchange = "#"
    # Both halves of rule 8 are one key per band: a Scandinavian entrant
    # counts each DXCC entity, everyone else each prefix number inside a
    # Scandinavian entity.  Which expression is the key is the entrant's
    # business -- see mult_sql().
    NumMults = 1
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 1

    def _prefixes(self) -> tuple:
        """The operator's and the worked station's country and continent."""
        parent = self.parent
        mine = ""
        my_continent = ""
        theirs = ""
        their_continent = ""
        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result:
            item = result.get(next(iter(result)))
            mine = item.get("primary_pfx", "")
            my_continent = item.get("continent", "")
        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result:
            item = result.get(next(iter(result)))
            theirs = item.get("primary_pfx", "")
            their_continent = item.get("continent", "")
        return mine, my_continent, theirs, their_continent

    def im_scandinavian(self) -> bool:
        """Is the operator in a Scandinavian DXCC entity?"""
        result = self.parent.cty_lookup(self.parent.station.get("Call", ""))
        if not result:
            return False
        item = result.get(next(iter(result)))
        return item.get("primary_pfx", "") in scandinavian_prefixes

    def mult_sql(self, slot):
        """The key rule 8 asks for, from the operator's side.

        8.1: a Scandinavian entrant counts each worked DXCC entity once per
        band -- the plain ``CountryPrefix`` column.
        8.2: everyone else counts each prefix number (0-9) inside each
        Scandinavian entity once per band, so the key is the entity and the
        third character of the worked station's WPX prefix.  A non-Scandinavian
        entity is not a multiplier at all, so the ``CASE`` returns NULL for it
        and the row drops out of the count.
        """
        if slot != 1:
            return super().mult_sql(slot)
        if self.im_scandinavian():
            return "CountryPrefix"
        entities = ", ".join(f"'{prefix}'" for prefix in scandinavian_prefixes)
        area = "COALESCE(substr(WPXPrefix, 3, 1), '')"
        return (
            f"CASE WHEN CountryPrefix = 'JW/b' THEN 'JW' || ':' || {area} "
            f"WHEN CountryPrefix IN ({entities}) "
            f"THEN CountryPrefix || ':' || {area} END"
        )

    def mult_value(self, slot, contact):
        """The same key in Python, for the log and the bandmap."""
        if slot != 1:
            return super().mult_value(slot, contact)
        prefix = str(contact.get("CountryPrefix", "") or "")
        if not prefix:
            result = self.parent.cty_lookup(contact.get("Call", ""))
            if result:
                item = result.get(next(iter(result)))
                prefix = str(item.get("primary_pfx", ""))
        if self.im_scandinavian():
            return prefix or None
        entity = scandinavian_entity({"CountryPrefix": prefix})
        if not entity:
            return None
        area = str(contact.get("WPXPrefix", "") or "")[2:3]
        return f"{entity}:{area}"

    def points(self):
        """Calc point"""
        # 7.1 For Scandinavian stations:
        #   EUROPEAN stations, outside Scandinavia, are worth two (2) points
        #   for every complete QSO.  NON-EUROPEAN stations are worth three (3)
        #   points for every complete QSO.
        # 7.2 For non-Scandinavian stations:
        #   EUROPEAN stations receive one (1) point for every complete
        #   Scandinavian QSO.  NON-EUROPEAN stations receive one (1) point for
        #   every complete Scandinavian QSO on 14, 21 and 28 MHz and three (3)
        #   points for every complete QSO on 3.5 and 7 MHz.
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        mine, my_continent, theirs, their_continent = self._prefixes()
        band = band_mhz_of(parent.contact.get("Band"))

        if mine in scandinavian_prefixes and theirs not in scandinavian_prefixes:
            if their_continent == "EU":
                return 2
            return 3
        if mine not in scandinavian_prefixes and theirs in scandinavian_prefixes:
            if my_continent == "EU":
                return 1
            if band in (3.5, 7.0):
                return 3
            if band in (14.0, 21.0, 28.0):
                return 1

        # Something wrong
        return 0

    def set_contact_vars(self):
        """Contest Specific"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()

    def recalculate_mults(self):
        """Mark nothing, as the module did.

        The module never wrote ``IsMultiplierN``: the multipliers are counted
        from the log, and the M column is not in the log window.  The base
        would otherwise start marking rows.
        """
