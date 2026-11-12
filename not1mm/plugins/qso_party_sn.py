"""
Generic State QSO Party (S/N + County)
-------------------------------------------------
Status:	Active
Geographic Focus:	US
Participation:	Worldwide
Mode:	CW, SSB, Digital
Bands:	160, 80, 40, 20, 15, 10, 6, 2m, 70cm
Classes:	Single Op (QRP/Low/High)
            Multi-Single (QRP/Low/High)
            Multi-Multi (QRP/Low/High)
Max operating hours:	Varies
Max power:	HP: >100 watts
LP: 100 watts
QRP: 5 watts
Exchange:	Serial No. + County/State/Country
Work stations:	Once per band per mode per location

Scoring:
Contact via phone: 1 point
Contact via CW: 2 points
Contact via digital: 2 points

Multipliers: County, State, or Country (aside from US/Canada) across all modes/bands: 1 point

Score Calculation:	Total score = total QSO points x total mults + bonus points
E-mail logs to:	(varies)
Mail logs to:	(varies)
Find rules at:	(varies)
Cabrillo name:	QSO_PARTY
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """Generic State QSO Party, serial number and county.

    The same template as :mod:`not1mm.plugins.qso_party_rst` with a serial
    number in place of the reports.  The county may be a county line
    ("ORAN/SBER"), which the Cabrillo writer expands.
    """

    DisplayName = "QSO PARTY SN"
    CabrilloName = "QSO_PARTY"
    # qso_party_rst carries the same Cabrillo name but a different exchange, so
    # the identifier is what tells the two apart (not1mm.lib.contest.contest_id).
    ContestName = "qso_party_sn"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# State/Prov or County"
    SOAPBOX_HINT = """
If you're on a county line enter each separated by a '/'
Example: # ORAN/SBER

Set Exchange macro to {EXCH}

If contact being logged is on a county line,
input each county separated by a '/'.
"""
    # Allow for rovers: the same station may be worked again.
    DupeType = 4
    Bands = (1.8, 3.5, 7, 14, 21, 28, 50, 144, 432)
    # The serials and the county/state/country; other_2 is unused.
    EntryFields = ("field1", "field2", "field3")
    FrameText = ("SentNR", "County/State/DX", "")
    RcvLabel = "RcvNR"
    AccessibleNames = ("SentNR", "RcvNR", "", "")
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
        "Operator",
    ]
    # Each county, state or country once for the whole contest.
    NumMults = 1
    Multiplier1Name = "County/State/DX"
    MultSqlString = "Exchange"
    IsMult1Per = 4

    def points(self):
        """Phone is one point, CW and the digital modes two.

        A mode the rules do not name scores nothing.
        """
        if self.parent.contact_is_dupe > 0:
            return 0
        mode = self.parent.contact.get("Mode", "")
        if mode in ("LSB", "USB", "SSB", "FM", "AM"):
            return 1
        if mode in (
            "CW",
            "CW-U",
            "CW-L",
            "CW-R",
            "CWR",
            "FT8",
            "FT4",
            "RTTY",
            "PSK31",
            "FSK441",
            "MSK144",
            "JT65",
            "JT9",
            "Q65",
            "PKTUSB",
            "PKTLSB",
        ):
            return 2
        return 0

    def set_contact_vars(self):
        """The serials and the received county/state/country."""
        parent = self.parent
        parent.contact["SentNr"] = parent.sent.text()
        parent.contact["NR"] = parent.receive.text()
        parent.contact["Exchange1"] = parent.other_1.text().upper()
        self.mark_multipliers()

    def prefill(self):
        """Fill the sent serial, if the operator has not typed one."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.sent.text()) == 0:
            parent.sent.setText(serial_nr)

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def cabrillo_mode(self, mode: str) -> str:
        """Phone is ``PH`` and RTTY is ``RY``.

        The generic template deliberately leaves the digital mode names alone
        ("dont simplify digital mode names"), so only the two Cabrillo names
        that must not be spelled any other way are mapped.
        """
        if mode in ("LSB", "USB", "SSB", "FM", "AM"):
            return "PH"
        if mode == "RTTY":
            return "RY"
        if mode in ("CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        return mode

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
        received = str(contact.get("Exchange1", "")).upper().strip()

        lines = []
        for mcl in location.split("/"):
            for the_qth in received.split("/"):
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
        """Show what the call history file knows about the call."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, "
                f"{result.get('Exch1', '')} {result.get('UserText', '')}".strip()
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Show the history and prefill the county field."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            county = result.get("Exch1", "")
            parent.history_info.setText(
                f"{county} {result.get('UserText', '')}".strip()
            )
            if county and not parent.other_1.text():
                parent.other_1.setText(county)
