"""California QSO Party plugin

Find rules at: https://www.cqp.org/Rules.html

160-10m, once per band and mode, three points a contact.  A California station
works everyone and counts each US state and Canadian province/territory; a
station elsewhere counts only the California counties it works.  The exchange
is a serial number and a county (in CA) or a state/province (outside), so the
multiplier is the mapped exchange rather than a column.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# California 4-letter county abbreviations (58 total)
# Used to validate CA station exchanges and for mult checking
CA_COUNTIES = {
    "ALAM",
    "ALPI",
    "AMAD",
    "BUTT",
    "CALA",
    "CCOS",
    "COLU",
    "DELN",
    "ELDO",
    "FRES",
    "GLEN",
    "HUMB",
    "IMPE",
    "INYO",
    "KERN",
    "KING",
    "LAKE",
    "LASS",
    "LANG",
    "MADE",
    "MARN",
    "MARP",
    "MEND",
    "MERC",
    "MODO",
    "MONO",
    "MONT",
    "NAPA",
    "NEVA",
    "ORAN",
    "PLAC",
    "PLUM",
    "RIVE",
    "SACR",
    "SBAR",
    "SBEN",
    "SBER",
    "SCLA",
    "SCRU",
    "SDIE",
    "SFRA",
    "SHAS",
    "SJOA",
    "SIER",
    "SISK",
    "SLUI",
    "SOLA",
    "SONO",
    "STAN",
    "SUTT",
    "SMAT",
    "TEHA",
    "TRIN",
    "TULA",
    "TUOL",
    "VENT",
    "YOLO",
    "YUBA",
}

# US state/province 2-letter abbreviations (63 total: 50 states + 13 Canadian)
# Used for CA station multipliers. DX does not count as a mult for CA stations.
CA_MULTS = {
    # US states
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    # Canadian provinces/territories
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NT",
    "NS",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}


def is_valid_ca_county(text: str) -> bool:
    """Return True if text is a valid 4-letter California county abbreviation."""

    return text.upper().strip() in CA_COUNTIES


def normalize_exchange(text: str) -> str:
    """Return the normalized (uppercased, stripped) exchange text."""

    return text.upper().strip()


def is_valid_state_province(text: str) -> bool:
    """True if text is a 2-letter US state or Canadian province."""

    return text.upper().strip() in CA_MULTS


def is_valid_exchange(text: str) -> bool:
    """True if text is a county, a state/province or ``DX``."""

    upper = text.upper().strip()
    return upper in CA_COUNTIES or upper in CA_MULTS or upper == "DX"


def points_for_qso(mode: str, is_dupe: bool) -> int:
    """Three points for phone and CW alike; a duplicate scores nothing.

    The mode is not consulted -- the party pays the same for every mode --
    but it is part of the signature so a caller has one place to ask.
    """

    if is_dupe:
        return 0
    return 3


class Contest(ContestBase):
    """California QSO Party."""

    DisplayName = "California QSO Party"
    CabrilloName = "CA-QSO-PARTY"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "# State/Prov or CA County."
    SOAPBOX_HINT = """California QSO Party

In CA set Sent Exchange to # and a 4 character county.
If you're on a county line enter each separated by a '/'
Example: # ORAN/SBER

Out of CA set it to # and a 2 char State/Prov.

Set Exchange macro to {EXCH}

If contact being logged is on a county line,
input each county separated by a '/'. 
"""
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    WritesGridLocator = False  # the CQP header has no GRID-LOCATOR line
    # The RST fields carry the serial numbers; the exchange is other_1.
    EntryFields = ("field1", "field2", "field3")
    FrameText = ("SentNR", "State/County", "")
    RcvLabel = "RcvNR"
    AccessibleNames = ("SentNR", "RcvNR", "State/County", "")
    NextField = "receive"
    ESMExchangeField = "other_1"  # the exchange is the first extra field
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "M1",
        "PTS",
    ]
    # The multiplier is the mapped exchange (see mult_value), once for the
    # contest; the score counts at most 58 of them.
    NumMults = 1
    Multiplier1Name = "State/County"
    MultSqlString = "Exchange"
    IsMult1Per = 4

    def is_ca_station(self) -> bool:
        """Is the operator in California?

        A California station works everyone and counts states and provinces; a
        station elsewhere counts only the California counties it works.
        """
        return str(self.parent.station.get("State", "")).strip().upper() == "CA"

    def multiplier_key(self, exchange: str):
        """Return the multiplier an exchange contributes, or None.

        A California station counts the state or province it is sent, and its
        first California county contact is its California multiplier whichever
        county it is.  A station elsewhere counts each California county.  DX
        and anything unrecognised contribute nothing.
        """
        exch = (exchange or "").upper().strip()
        if self.is_ca_station():
            if exch in CA_COUNTIES:
                return "CA"
            if exch in CA_MULTS:
                return exch
            return None
        return exch if exch in CA_COUNTIES else None

    def mult_value(self, slot: int, contact):
        """The mapped exchange, not the column the base would read."""
        return self.multiplier_key(contact.get("Exchange1", ""))

    def cabrillo_mode(self, mode: str) -> str:
        """Phone is ``PH``; the digital modes keep their own names."""
        if mode in ("LSB", "USB", "SSB", "FM", "AM"):
            return "PH"
        return super().cabrillo_mode(mode)

    def points(self):
        """3 points a contact, phone and CW alike.

        A station outside California only scores the California stations it
        works, which send a 4-letter county: non-CA to non-CA contacts count
        for neither credit nor penalty, so they score nothing.
        """
        if self.parent.contact_is_dupe > 0:
            return 0
        if not self.is_ca_station() and not is_valid_ca_county(
            self.parent.contact.get("Exchange1", "")
        ):
            return 0
        return points_for_qso(self.parent.contact.get("Mode", ""), False)

    def set_contact_vars(self):
        """The serials and the exchange, then the multiplier."""
        parent = self.parent
        parent.contact["SentNr"] = parent.sent.text()
        parent.contact["NR"] = parent.receive.text()
        parent.contact["Exchange1"] = normalize_exchange(parent.other_1.text())
        self.mark_multipliers()

    def mark_multipliers(self):
        """Mark the contact as a new multiplier, using the mapped key.

        The key is not a column, so the base's SQL existence check cannot be
        used; the log is scanned and its keys mapped instead.
        """
        contact = self.parent.contact
        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = 0
        key = self.multiplier_key(contact.get("Exchange1", ""))
        if key is None:
            return
        seen = {
            self.multiplier_key(row.get("Exchange1", ""))
            for row in self.parent.database.fetch_all_contacts_asc()
        }
        if key not in seen:
            contact["IsMultiplier1"] = 1

    def show_mults(self):
        """The states/provinces (or the counties) worked, at most 58.

        A California station counts the US states (California through its first
        county contact) and Canadian provinces/territories it is sent, DX
        excepted; a station elsewhere counts the California counties it works.
        Either way the score counts at most 58.
        """
        seen = set()
        for row in self.parent.database.fetch_all_contacts_asc():
            key = self.multiplier_key(row.get("Exchange1", ""))
            if key is not None:
                seen.add(key)
        return min(len(seen), 58)

    def get_mults(self):
        """The score page wants the state count."""
        return {"state": self.show_mults()}

    def recalculate_mults(self):
        """Re-mark the first contact of each multiplier."""
        seen = set()
        for contact in self.parent.database.fetch_all_contacts_asc():
            contact["IsMultiplier1"] = 0
            key = self.multiplier_key(contact.get("Exchange1", ""))
            if key is not None and key not in seen:
                seen.add(key)
                contact["IsMultiplier1"] = 1
            self.parent.database.change_contact(contact)
        self.after_recalculate_mults()

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def prefill(self):
        """Fill the sent serial, if the operator has not typed one."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.sent.text()) == 0:
            parent.sent.setText(serial_nr)

    def cabrillo_qso_lines(self, contact):
        """One line per county pair, for a contact on a county line."""
        parent = self.parent
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        themode = self.cabrillo_mode(contact.get("Mode", ""))
        sent_nr = str(contact.get("SentNr", "")).strip()
        recv_nr = str(contact.get("NR", "")).strip()

        location = "*              "
        if contact.get("RoverLocation", ""):
            location = str(contact.get("RoverLocation", "")).upper().strip()
        elif parent.contest_settings.get("SentExchange", ""):
            location = (
                str(parent.contest_settings.get("SentExchange", ""))
                .upper()
                .strip("# ")
            )
        sent_qth = str(contact.get("Exchange1", "")).upper().strip()

        # In Cabrillo our sent QTH goes in sent position, their received QTH in
        # received position:
        # QSO: freq mo date time my_call sent_nr sent_qth their_call recv_nr recv_qth
        lines = []
        for mcl in location.split("/"):
            for the_qth in sent_qth.split("/"):
                lines.append(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{sent_nr.ljust(6)} "
                    f"{mcl.ljust(5)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{recv_nr.ljust(6)} "
                    f"{the_qth.ljust(5)}"
                )
        return lines

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result and parent.other_1.text() == "":
            parent.other_1.setText(f"{result.get('Exch1', '')}")
