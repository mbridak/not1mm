"""Winter Field Day plugin

Find rules at: https://winterfieldday.org/downloads/2026-rules-v3.pdf

160-10m, once per band and mode.  The exchange is the class (``1O``, ``2A``,
...) and the ARRL/RAC section; phone is 1 point and CW or digital 2 (FT4 and
FT8 do not count), and the score is the points times the number of band/mode
combinations worked, doubled for a QRP entrant (rule 7).

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM", "PH")
# "Digital includes PSK, RTTY, Olivia, Packet, SSTV, ATV, JS8Call, and other
# soundcard modes except for FT4 & FT8." Winter Field Day does not allow them.
_NO_POINT_MODES = ("FT4", "FT8")

# The sponsor's Cabrillo spelling for the digital modes.
_DIGITAL_MODES = (
    "BPSK31",
    "CONTESTI",
    "DOMINO",
    "FSQ",
    "FT8",
    "FT4",
    "HELL",
    "IFKP",
    "RTTY",
    "PSK",
    "PSK31",
    "FSK441",
    "MFSK",
    "MSK144",
    "MT63",
    "OLIVIA",
    "JS8",
    "JT65",
    "JT9",
    "Q65",
    "SCAMP",
    "THOR",
    "THRB",
)


def _points_for_mode(mode: str) -> int:
    """Phone 1 point; CW and digital 2; FT4/FT8 score nothing."""
    upper = str(mode).upper()
    if not upper or upper in _NO_POINT_MODES:
        return 0
    if upper in _PHONE_MODES:
        return 1
    return 2


class Contest(ContestBase):
    """Winter Field Day."""

    DisplayName = "Winter Field Day"
    CabrilloName = "WFD"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "1O ORG"
    SupportsFT8 = True
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # Only the class and section fields are used; the RSTs are hidden.
    EntryWindowInfo = ("Exchange1Text", 615, "SectText", 600)
    QsoErrorString = "Exchange1Text_Any_not_Empty, SectText_Any_not_Empty"
    FrameText = ("Class", "Section")
    AccessibleNames = (
        "Class",
        "Section",
    )
    # The module focused the class field after a lookup, not the section.
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Exchange1",
        "Sect",
        "PTS",
    ]
    # The score is the points times the number of band/mode combinations worked,
    # not a keyed multiplier, so show_mults() is that count and the declared
    # slot only names the score-page row the module reported.
    NumMults = 1
    Multiplier1Name = "Prefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 4

    def points(self):
        """1 point phone, 2 CW or digital, nothing for FT4/FT8."""
        if self.parent.contact_is_dupe > 0:
            return 0
        return _points_for_mode(self.parent.contact.get("Mode", ""))

    def show_mults(self):
        """The number of band/mode combinations worked."""
        result = self.parent.database.get_unique_band_and_mode()
        return int(result.get("mult", 0)) if result else 0

    def calc_score(self):
        """The points times the combinations, doubled for a QRP entrant."""
        power = self.parent.contest_settings.get("PowerCategory", "")
        return super().calc_score() * (2 if power == "QRP" else 1)

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""

    def set_contact_vars(self):
        """The exchange; the class and section are the received ones."""
        parent = self.parent
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Exchange1"] = parent.fields.Exchange1Text.text().upper()
        parent.contact["Sect"] = parent.fields.SectText.text().upper()

    def prefill(self):
        """Nothing to prefill: Exchange1Text is the class, not the sent exchange."""

    def cabrillo_mode(self, mode: str) -> str:
        """CW, PH or DG, as the sponsor spells them."""
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "FM", "AM"):
            return "PH"
        if str(mode).upper() in _DIGITAL_MODES:
            return "DG"
        return mode

    def cabrillo_qso_line(self, contact):
        """The Field Day line: the operator's own exchange, then class/section."""
        parent = self.parent
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        sent = parent.contest_settings.get("SentExchange", "").ljust(9).upper()
        return (
            f"QSO: {frequency} "
            f"{self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{sent}"
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Exchange1', '')).ljust(3)} "
            f"{str(contact.get('Sect', '')).ljust(6)}"
        )

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = self.report_default()
        parent.contact["RCV"] = self.report_default()
        parent.contact["Exchange1"] = packet.get("CLASS", "ERR")
        parent.contact["Sect"] = packet.get("ARRL_SECT", "ERR")
        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.fields.Exchange1Text.setText(packet.get("CLASS", "ERR"))
        parent.fields.SectText.setText(packet.get("ARRL_SECT", "ERR"))
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the class, section and user text for the typed call."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('Sect', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the class and section from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.fields.Exchange1Text.text() == "":
                parent.fields.Exchange1Text.setText(f"{result.get('Exch1', '')}")
            if parent.fields.SectText.text() == "":
                parent.fields.SectText.setText(f"{result.get('Sect', '')}")
