"""ARRL 10 Meter plugin

Find rules at: http://www.arrl.org/10-meter

10m only, once per band and mode.  Phone is 2 points and CW 4; the multipliers
are each state/province (or the serial a station outside W/VE sends), each
``/MM`` and each DXCC country, once per mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM", "PH")
_CW_MODES = ("CW", "CW-U", "CW-L", "CWR", "CW-R")


class Contest(ContestBase):
    """ARRL 10 Meter."""

    DisplayName = "ARRL 10M"
    CabrilloName = "ARRL-10"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "State/Province"
    SOAPBOX_HINT = """If you’re exchange is (RST + Serial No.) You should edit your exchange macro keys to be '{SNT} {SENTNR}' and a '#' character in the sent exchange field above.

If you’re exchange is (RST + State/Province/ITU), you should edit your exchange macro keys to be '{SNT} {EXCH}' and your state/prov/itu in the sent exchange field above.
"""
    SendsRTCScore = True
    Bands = (28,)
    FrameText = ("SNT", "SentNR", "State|Prov|SN|ITU")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "State Province Serial Number or I T U Section",
    )
    # A state/province (or a serial), a /MM and a DXCC country, each once per
    # mode; the two halves are counted separately (see show_mults).
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 2

    def points(self):
        """2 points phone, 4 CW (rule 5.1)."""
        if self.parent.contact_is_dupe > 0:
            return 0
        mode = str(self.parent.contact.get("Mode", "")).upper()
        if mode in _PHONE_MODES:
            return 2
        if mode in _CW_MODES:
            return 4
        return 0

    def show_mults(self, rtc=None):
        """States/provinces and /MM once per mode, plus DXCC once per mode.

        A W/VE station sends its state/province (stored as text), everyone else
        a serial (stored as an integer), so the two are told apart by ``typeof``;
        a ``/MM`` is counted as a second station rather than a country.
        """
        database = self.parent.database
        contest = database.current_contest
        us_ve_mx = database.exec_sql(
            "select count(DISTINCT(NR || ':' || Mode)) as mult_count "
            f"from dxlog where ContestNR = {contest} and typeof(NR) = 'text';"
        ).get("mult_count", 0)
        mm = database.exec_sql(
            "select count(DISTINCT(NR || ':' || Mode)) as mult_count "
            f"from dxlog where ContestNR = {contest} "
            "and typeof(NR) = 'integer' and call like '%/MM';"
        ).get("mult_count", 0)
        dx = database.exec_sql(
            "select count(DISTINCT(CountryPrefix || ':' || Mode)) as mult_count "
            f"from dxlog where ContestNR = {contest} "
            "and typeof(NR) = 'integer' and call not like '%/MM';"
        ).get("mult_count", 0)
        if rtc is not None:
            return dx, us_ve_mx + mm
        return us_ve_mx + mm + dx

    def get_mults(self):
        """The score page wants the country and the state counts separately."""
        country, state = self.show_mults(rtc=True)
        return {"country": country, "state": state}

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1`` (see §28)."""

    def set_contact_vars(self):
        """The exchange; the received one is a state/province or a serial."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
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
                parent.other_2.setText(f"{result.get('State', '')}")
