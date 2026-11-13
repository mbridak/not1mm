"""RSGB 3.5MHz Club Championship (80m CC)

Find rules at: https://www.rsgbcc.org/hf/rules/2026/r80mcc.shtml

80m only, in sessions of 90 minutes per mode.  A UK&CD station must be at one
or both ends of a contact for it to score -- one point, or five against the
Society's station, G6XX or a regional variant.  There are no multipliers, so
the score is the sum of the points.

A station may be worked once per mode in a session, with RTTY and the PSK
family kept apart: rule 6 lets a station be worked "once on PSK63 and once on
RTTY".

The RSGB 3.5MHz Autumn Series (Cabrillo RSGB-80M-AUT) is a similar series
sharing this Cabrillo format and these per-QSO rules, but it adds a
licence-class multiplier for club scores and a "Le Mans" start penalty, and it
is not covered by this plugin.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import re

from not1mm.lib.contest import ContestBase, output_cabrillo_line
from not1mm.lib.version import __version__

# Rule 6: a UK&CD station is required at one or both ends of a contact for it
# to count for points.  CD is the Crown Dependencies; the Republic of Ireland
# is a separate country and is not part of UK&CD.
UKCD_ENTITIES = (
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
    "Guernsey",
    "Jersey",
    "Isle of Man",
)

# The Society's station is G6XX and its regional variants.  The regional
# secondary locator follows either G or M - Wales is GW6XX or MW6XX, Scotland
# is GM6XX or MM6XX - so both spellings have to be recognised.  A bare M6XX is
# deliberately not matched: that is an ordinary English full-licence call.
RSGB_STATION_RE = re.compile(r"^(?:G|G[DEIJMUW]|M[DEIJMUW])6XX$")


def is_rsgb_station(call: str) -> bool:
    """Rule 6: the Society's station, G6XX or a regional variant, scores 5."""
    return bool(RSGB_STATION_RE.match(str(call).upper().split("/")[0]))


def _dupe_mode(mode: str) -> str:
    """Group a mode for dupe checking.

    Phone modes are one group and the CW variants another, so a station worked
    on LSB and again on USB is still a dupe.  RTTY and the PSK family stay
    apart from each other, because rule 6 lets a station be worked "once on
    PSK63 and once on RTTY".
    """
    upper = str(mode).upper()
    if upper.startswith("PSK") or upper.startswith("BPSK"):
        return "PSK"
    if upper.startswith("RTTY") or upper in ("FSK", "RY"):
        return "RTTY"
    if upper in ("LSB", "USB", "SSB", "FM", "AM", "PH"):
        return "PH"
    if upper.startswith("CW"):
        return "CW"
    return upper


# Rule 7: "check that you have used the correct Cabrillo Mode Codes: RTTY =
# RY, PSK63 = PS, PK or PM, SSB = PH, CW = CW".  A rig reports PSK31 rather
# than PSK63, so the PSK family has to be matched as a group.
CABRILLO_MODE = {"CW": "CW", "PH": "PH", "RTTY": "RY", "PSK": "PS"}


class Contest(ContestBase):
    """RSGB 3.5MHz Club Championship (80m CC)."""

    DisplayName = "RSGB 80M CC"
    CabrilloName = "RSGB-80M-CC"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "#"
    # The exchange is a serial, so "#" is what an empty setup sends.
    DefaultContestExchange = "#"
    # The sessions are single-band, and the DATA ones count PSK63 and RTTY as
    # different modes, so "once per session" is once per mode with those two
    # kept apart -- the contest's own rule.
    DupeType = 5
    Bands = (3.5,)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
    ]
    SendsRTCScore = True

    def _is_ukcd(self, call) -> bool:
        """Return True if `call` is in the UK, the Crown Dependencies or NI."""
        result = self.parent.cty_lookup(call)
        if result is not None:
            item = result.get(next(iter(result)))
            return item.get("entity", "") in UKCD_ENTITIES
        return False

    def specific_contest_check_dupe(self, call):
        """Rule 6: a station may be worked once per mode in this session.

        The sessions are single-band, so "once per session" is once per mode.
        A duplicate still has to be logged - it just scores nothing.
        """
        parent = self.parent
        state = getattr(parent, "radio_state", None) or {}
        want = _dupe_mode(state.get("mode") or parent.contact.get("Mode", ""))
        for contact in parent.database.fetch_all_contacts_asc():
            if str(contact.get("Call", "")).upper() != str(call).upper():
                continue
            if _dupe_mode(contact.get("Mode", "")) == want:
                return {"isdupe": True}
        return {"isdupe": False}

    def points(self):
        """One point, five against the Society's station, none without UK&CD."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        # Rule 6: a UK&CD station must be at one or both ends of the contact.
        if not (
            self._is_ukcd(parent.station.get("Call", ""))
            or self._is_ukcd(parent.contact.get("Call", ""))
        ):
            return 0

        # Rule 6: QSOs with the Society's station are worth five points.
        if is_rsgb_station(parent.contact.get("Call", "")):
            return 5

        return 1

    def cabrillo_mode(self, mode: str) -> str:
        """The RSGB codes: the whole PSK family is `PS`, not Cabrillo's PM/PO."""
        return CABRILLO_MODE.get(_dupe_mode(mode), mode)

    def _cabrillo_header(self, file_descriptor, file_encoding):
        """The RSGB 80m CC header: no LOCATION, five ADDRESS lines."""
        parent = self.parent
        station = parent.station
        settings = parent.contest_settings

        def line(text):
            output_cabrillo_line(text, "\r\n", file_descriptor, file_encoding)

        line("START-OF-LOG: 3.0")
        line(f"CREATED-BY: Not1MM v{__version__}")
        line(f"CONTEST: {self.CabrilloName}")
        if station.get("Club", ""):
            line(f"CLUB: {station.get('Club', '').upper()}")
        line(f"CALLSIGN: {station.get('Call', '')}")
        line(f"CATEGORY-OPERATOR: {settings.get('OperatorCategory', '')}")
        line(f"CATEGORY-ASSISTED: {settings.get('AssistedCategory', '')}")
        line(f"CATEGORY-BAND: {settings.get('BandCategory', '')}")
        line(f"CATEGORY-MODE: {self.cabrillo_category_mode()}")
        if settings.get("OverlayCategory", "") != "N/A":
            line(f"CATEGORY-OVERLAY: {settings.get('OverlayCategory', '')}")
        line(f"GRID-LOCATOR: {station.get('GridSquare', '')}")
        line(f"CATEGORY-POWER: {settings.get('PowerCategory', '')}")
        line(f"CLAIMED-SCORE: {self.calc_score()}")
        ops = ""
        for op in parent.database.get_ops():
            ops += f"{op.get('Operator', '')}, "
        if station.get("Call", "") not in ops:
            ops += f"@{station.get('Call', '')}"
        else:
            ops = ops.rstrip(", ")
        line(f"OPERATORS: {ops}")
        line(f"NAME: {station.get('Name', '')}")
        line(f"ADDRESS: {station.get('Street1', '')}")
        line(f"ADDRESS: {station.get('City', '')}")
        line(f"ADDRESS: {station.get('Zip', '')}")
        line(f"ADDRESS: {station.get('Country', '')}")
        line(f"ADDRESS: {station.get('Email', '')}")
