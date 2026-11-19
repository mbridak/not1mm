"""ARRL 160-Meter plugin

Find rules at: http://www.arrl.org/160-meter

160m only, once per contest.  W/VE stations exchange their ARRL/RAC section,
everyone else just a report; a W/VE-to-W/VE contact is 2 points and a W/VE-to-DX
contact 5 (rule 5.1), and a DX-to-DX contact scores nothing (rule 2.2).  A W/VE
entrant counts each DXCC country and each section worked; a DX entrant counts
the sections only.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# Rule 2.1.1: Alaska (KL7 - AK), Hawaii (KH6 - PAC), the Caribbean US
# possessions (KP1-KP5) and the Pacific Ocean territories (KH0-KH9)
# participate as W/VE stations and count as ARRL sections.
WVE_PREFIXES = (
    "K",
    "KL",
    "KH0",
    "KH1",
    "KH2",
    "KH3",
    "KH4",
    "KH5",
    "KH6",
    "KH7",
    "KH8",
    "KH9",
    "KP1",
    "KP2",
    "KP3",
    "KP4",
    "KP5",
    "VE",
)


class Contest(ContestBase):
    """ARRL 160-Meter."""

    DisplayName = "ARRL 160-Meter"
    CabrilloName = "ARRL-160"
    Mode = "CW"
    DupeType = 1  # once per contest
    EXCHANGE_HINT = "ST/Prov or DX report only"
    SendsRTCScore = True
    Bands = (1.8,)
    # The received exchange is the section, in Exchange1Text.
    EntryWindowInfo = ("SNTText", 450, "RCVText", 450, "Exchange1Text", 615)
    FrameText = ("SNT", "RCV", "ARRL/RAC Section")
    AccessibleNames = (
        "RST Sent",
        "RST Received",
        "Received Exchange",
    )
    QsoErrorString = "Exchange1Text_Any_not_Empty"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "PFX",
        "Exchange1",
        "PTS",
    ]
    # A DXCC country (W/VE only) and a section, each once for the contest.
    NumMults = 1
    Multiplier1Name = "Sect"
    MultSqlString = "Sect"
    IsMult1Per = 4

    def _is_wve(self, call):
        """Is *call* in W/VE (rule 2.1.1)?"""
        result = self.parent.cty_lookup(call)
        if result is None:
            return False
        item = result.get(next(iter(result)))
        return item.get("primary_pfx", "") in WVE_PREFIXES

    def can_claim_dxcc(self):
        """May we claim DXCC multipliers -- are we the W/VE side?"""
        return self._is_wve(self.parent.station.get("Call", ""))

    def points(self):
        """2 points W/VE to W/VE, 5 to DX, nothing DX to DX (rules 5.1, 2.2)."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        mine = self._is_wve(parent.station.get("Call", ""))
        theirs = self._is_wve(parent.contact.get("Call", ""))
        if mine and theirs:
            return 2
        if mine or theirs:
            return 5
        return 0

    def show_mults(self):
        """A DXCC country (W/VE only) plus each section, once for the contest."""
        database = self.parent.database
        dxcc = 0
        if self.can_claim_dxcc():
            dxcc = int(database.fetch_country_count().get("dxcc_count", 0))
        sections = int(database.fetch_exchange1_unique_count().get("exch1_count", 0))
        return dxcc + sections

    def get_mults(self):
        """The score page wants the country and the state counts separately."""
        mults = {"state": self._section_count()}
        if self.can_claim_dxcc():
            mults["country"] = self.parent.database.fetch_country_count().get(
                "dxcc_count", 0
            )
        return mults

    def _section_count(self):
        """The number of distinct received sections."""
        result = self.parent.database.fetch_exchange1_unique_count()
        return result.get("exch1_count", 0)

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1`` (see §28)."""

    def set_contact_vars(self):
        """The exchange; the received section is stored in ``Exchange1``."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        parent.contact["Exchange1"] = parent.fields.Exchange1Text.text()

    def cabrillo_qso_line(self, contact):
        """The base's line, but the received exchange is ``Exchange1``.

        A station outside W/VE sends only a report, so a missing exchange is
        written as ``---`` rather than left blank.
        """
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        sentnr = contact.get("SentNr", "---") or "---"
        exchange = contact.get("Exchange1", "---") or "---"
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(sentnr).ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(exchange).ljust(6)}"
        )

    def esm_exchange_ready(self):
        """A DX station sends no section; only a W/VE one has one to copy."""
        if self.parent.contact.get("CountryPrefix", "") not in ("K", "VE"):
            return True
        return super().esm_exchange_ready()

    def populate_history_info_line(self):
        """Show history info if available."""
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
        """Prefill the received section from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.Exchange1Text.text() == "":
                parent.fields.Exchange1Text.setText(f"{result.get('Exch1', '')}")
