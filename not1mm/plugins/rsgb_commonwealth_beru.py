"""RSGB Commonwealth (BERU) Contest

Find rules at: https://www.rsgbcc.org/hf/rules/2025/rcwc.shtml

80m to 10m, CW, once per band.  Only Commonwealth Call Area stations may
enter, and a contact inside the entrant's own call area does not count; the
seven UK home nations do not count against each other either, but an HQ
station may be worked by anyone.  A contact is 5 points within a continent and
10 across it, plus 20 bonus points for each of the first three contacts with a
Commonwealth Call Area on each band.  There are no multipliers, so the score is
the sum of the points.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import re

from not1mm.lib.contest import ContestBase

# The seven UK home nations / crown dependencies listed in rule 4(d).
# Contacts between any two of these areas score nothing unless the
# distant station is an HQ station.
HOME_NATIONS = frozenset(
    (
        "England",
        "Northern Ireland",
        "Scotland",
        "Wales",
        "Isle of Man",
        "Jersey",
        "Guernsey",
    )
)

# DXCC entity names as they appear in data/cty.json, covering the
# RSGB Commonwealth Call Areas list:
# https://www.rsgbcc.org/hf/information/codes.shtml
COMMONWEALTH_ENTITIES = frozenset(
    (
        # United Kingdom, Crown Dependencies and Overseas Territories
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
        "Isle of Man",
        "Jersey",
        "Guernsey",
        "Gibraltar",
        "Bermuda",
        "Anguilla",
        "Montserrat",
        "British Virgin Islands",
        "Turks & Caicos Islands",
        "Cayman Islands",
        "Falkland Islands",
        "South Georgia Island",
        "South Sandwich Islands",
        "South Shetland Islands",
        "South Orkney Islands",
        "Pitcairn Island",
        "Ducie Island",
        "St. Helena",
        "Ascension Island",
        "Tristan da Cunha & Gough",
        "Chagos Islands",
        # Europe
        "Malta",
        "Cyprus",
        "UK Base Areas on Cyprus",
        # Asia
        "India",
        "Andaman & Nicobar Is.",
        "Lakshadweep Islands",
        "Pakistan",
        "Bangladesh",
        "Sri Lanka",
        "Singapore",
        "West Malaysia",
        "East Malaysia",
        "Maldives",
        "Brunei Darussalam",
        "Spratly Islands",
        # Africa
        "South Africa",
        "Pr. Edward & Marion Is.",
        "Kingdom of Eswatini",
        "Lesotho",
        "Malawi",
        "Tanzania",
        "Nigeria",
        "Togo",
        "Uganda",
        "Kenya",
        "Ghana",
        "Sierra Leone",
        "Zambia",
        "Rwanda",
        "Botswana",
        "The Gambia",
        "Mozambique",
        "Namibia",
        "Gabon",
        "Cameroon",
        "Agalega & St. Brandon",
        "Mauritius",
        "Rodriguez Island",
        "Seychelles",
        # Americas
        "Canada",
        "Sable Island",
        "St. Paul Island",
        "Jamaica",
        "Barbados",
        "Trinidad & Tobago",
        "Antigua & Barbuda",
        "Belize",
        "St. Kitts & Nevis",
        "St. Lucia",
        "St. Vincent",
        "Dominica",
        "Grenada",
        "Bahamas",
        "Guyana",
        # Oceania
        "Australia",
        "Heard Island",
        "Macquarie Island",
        "Cocos (Keeling) Islands",
        "Christmas Island",
        "Lord Howe Island",
        "Mellish Reef",
        "Norfolk Island",
        "Willis Island",
        "New Zealand",
        "Chatham Islands",
        "Kermadec Islands",
        "N.Z. Subantarctic Is.",
        "Fiji",
        "Rotuma Island",
        "Conway Reef",
        "Papua New Guinea",
        "Nauru",
        "Tonga",
        "Samoa",
        "Niue",
        "North Cook Islands",
        "South Cook Islands",
        "Tuvalu",
        "Western Kiribati",
        "Central Kiribati",
        "Eastern Kiribati",
        "Banaba Island",
        "Tokelau Islands",
        "Temotu Province",
        "Solomon Islands",
        "Vanuatu",
    )
)

# Call area extraction for countries that contain multiple call areas.
CANADA_CALLAREA_RE = re.compile(r"^(V[EOY][0-9])")
AUSTRALIA_CALLAREA_RE = re.compile(r"^(VK9[CLMNWX]|VK[0-9])")
SOUTHAFRICA_CALLAREA_RE = re.compile(r"^(ZS[0-8])")
NEWZEALAND_CALLAREA_RE = re.compile(r"^(ZL[0-9])")

HQ_EXCHANGE_RE = re.compile(r"\bHQ\b", re.IGNORECASE)

# Portable markers that don't indicate the operating location,
# mirroring lib.ham_utility.calculate_wpx_prefix.
PORTABLE_SUFFIXES = [
    "M",
    "MM",
    "P",
    "QRP",
    "A",
    "J",
    "LH",
    "LGT",
    "LS",
    "NLD",
    "T",
    "R",
    "TR",
]


def get_base_call(call: str) -> str:
    """Return the callsign identifying the operating location.

    Strips portable markers and prefers a portable prefix (VE3/G4ABC -> VE3).

    Parameters
    ----------
    call : str
    The callsign to reduce to its base form.

    Returns
    -------
    str
    The base callsign.
    """

    base_call = str(call).upper().strip()
    if not base_call:
        return ""
    for suffix in PORTABLE_SUFFIXES:
        base_call = re.sub("/" + suffix + "$", "", base_call)
    if "/" in base_call:
        parts = [part for part in base_call.split("/") if part]
        with_digit = [
            part
            for part in parts
            if any(char.isdigit() for char in part)
            and any(char.isalpha() for char in part)
        ]
        if len(with_digit) > 1:
            return min(with_digit, key=len)
        if with_digit:
            return with_digit[0]
        if parts:
            return max(parts, key=len)
        return ""
    return base_call


def is_hq_station(exchange: str) -> bool:
    """Is the received exchange an HQ station's?

    HQ stations identify by sending 'HQ' after their serial number, and the
    token has to stand alone: "12HQ3" is not one.
    """
    return bool(HQ_EXCHANGE_RE.search(str(exchange)))


class Contest(ContestBase):
    """RSGB Commonwealth (BERU) Contest."""

    DisplayName = "RSGB Commonwealth BERU"
    CabrilloName = "RSGB-COMMONWEALTH"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    # The exchange is a serial, so "#" is what an empty setup sends.
    DefaultContestExchange = "#"
    DupeType = 2  # work each band once
    Bands = (3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M2",
        "PTS",
    ]
    # The RSGB header has no GRID-LOCATOR line.
    WritesGridLocator = False
    SendsRTCScore = True

    def get_entity_info(self, call: str) -> dict | None:
        """Look up DXCC entity information for a callsign."""
        result = self.parent.cty_lookup(get_base_call(call))
        if result is None:
            return None
        try:
            return result.get(next(iter(result)))
        except StopIteration:
            return None

    def get_commonwealth_area(self, call: str) -> str | None:
        """Return an identifier for the Commonwealth Call Area of a callsign.

        Countries containing multiple call areas are identified by their call
        area prefix, everything else by its DXCC entity name.
        """
        base_call = get_base_call(call)
        for pattern in (
            CANADA_CALLAREA_RE,
            AUSTRALIA_CALLAREA_RE,
            SOUTHAFRICA_CALLAREA_RE,
            NEWZEALAND_CALLAREA_RE,
        ):
            match = pattern.match(base_call)
            if match:
                return match.group(1)
        entity_info = self.get_entity_info(base_call)
        if entity_info is not None:
            return entity_info.get("entity")
        return None

    def scoring_info(self) -> dict | None:
        """Gather all information needed to score the current contact.

        Returns a dict with keys eligible, same_continent, hq_station, or None
        when either callsign cannot be resolved to an entity.
        """
        parent = self.parent
        hq_station = is_hq_station(str(parent.contact.get("NR", "")))

        my_info = self.get_entity_info(parent.station.get("Call", ""))
        their_info = self.get_entity_info(parent.contact.get("Call", ""))
        if my_info is None or their_info is None:
            return None

        my_continent = my_info.get("continent", "")
        their_continent = their_info.get("continent", "")
        their_entity = their_info.get("entity", "")

        my_area = self.get_commonwealth_area(parent.station.get("Call", ""))
        their_area = self.get_commonwealth_area(parent.contact.get("Call", ""))

        eligible = hq_station or their_entity in COMMONWEALTH_ENTITIES

        # Rule 4(b): no contacts within your own call area.
        # Rule 4(e): HQ stations may be contacted even in your own call area.
        if my_area is not None and my_area == their_area and not hq_station:
            eligible = False

        # Rule 4(d): QSOs between the seven home nations don't count,
        # unless the distant station is an HQ station.
        if not hq_station and my_area in HOME_NATIONS and their_area in HOME_NATIONS:
            eligible = False

        return {
            "eligible": eligible,
            "same_continent": my_continent == their_continent,
            "hq_station": hq_station,
        }

    def bonus_count_before_me(self) -> int:
        """Earlier contacts on this band that earned a Commonwealth bonus."""
        contact = self.parent.contact
        band = float(contact.get("Band", 0))
        time_stamp = contact.get("TS", "")
        query = (
            "select count(*) as bonus_count from dxlog "
            f"where Band={band} and IsMultiplier2=1 "
            f"and TS < '{time_stamp}' "
            f"and ContestNR = {self.parent.pref.get('contest', '1')};"
        )
        result = self.parent.database.exec_sql(query)
        return int(result.get("bonus_count", 0))

    def set_contact_vars(self):
        """The exchange, and the per-band Commonwealth Call Area bonus."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text()
        parent.contact["IsMultiplier1"] = 0
        info = self.scoring_info()
        if info is not None and info["eligible"]:
            # IsMultiplier2 marks a contact earning one of the three
            # per-band Commonwealth Call Area bonuses.
            if self.bonus_count_before_me() < 3:
                parent.contact["IsMultiplier2"] = 1
            else:
                parent.contact["IsMultiplier2"] = 0
        else:
            parent.contact["IsMultiplier2"] = 0

    def points(self):
        """5 within a continent, 10 across it, 20 more for a bonus contact."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        info = self.scoring_info()
        if info is None or not info["eligible"]:
            return 0

        if info["same_continent"]:
            contact_points = 5
        else:
            contact_points = 10

        # Rule 8(c): 20 additional points for each of the first three
        # contacts with a Commonwealth Call Area on each band.
        if int(parent.contact.get("IsMultiplier2", 0)) == 1:
            contact_points += 20
        return contact_points

    def recalculate_mults(self):
        """Replay the log to recompute the points and the per-band bonuses."""
        parent = self.parent
        all_contacts = parent.database.fetch_all_contacts_asc()
        bonus_counts = {}
        worked = set()
        for contact in all_contacts:
            parent.contact = contact
            key = (contact.get("Call", ""), contact.get("Band", ""))
            is_dupe = key in worked
            worked.add(key)
            parent.contact_is_dupe = 1 if is_dupe else 0
            info = self.scoring_info()
            earns_bonus = 0
            # A duplicate is not a valid contact, so it neither scores nor
            # takes one of the three bonus places on the band.
            if not is_dupe and info is not None and info["eligible"]:
                band = float(contact.get("Band", 0))
                count = bonus_counts.get(band, 0)
                if count < 3:
                    earns_bonus = 1
                bonus_counts[band] = count + 1
            contact["IsMultiplier1"] = 0
            contact["IsMultiplier2"] = earns_bonus
            contact["Points"] = self.points()
            parent.database.change_contact(contact)
