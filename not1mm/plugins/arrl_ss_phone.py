"""ARRL Sweepstakes Phone plugin

Find rules at: https://contests.arrl.org/ContestRules/SS-Rules.pdf

160/80/40/20/15/10m, once per contest.  The exchange is "serial precedence call
check section"; W/VE stations only score each other (rule 2.1), and each
ARRL/RAC section is a multiplier once for the whole contest (rule 5.2).

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from PyQt6 import QtWidgets

from not1mm.lib.contest import ContestBase

# The ARRL/RAC sections: the multipliers, and the only valid received exchange.
# Anything else means the station worked is not in W/VE and does not score for a
# W/VE entrant (rule 2.1).
ARRL_SECTIONS = frozenset(
    (
        "CO",
        "IA",
        "KS",
        "MN",
        "MO",
        "ND",
        "NE",
        "SD",
        "CT",
        "EMA",
        "ME",
        "NH",
        "RI",
        "VT",
        "WMA",
        "ENY",
        "NLI",
        "NNJ",
        "NNY",
        "SNJ",
        "WNY",
        "DE",
        "EPA",
        "MDC",
        "WPA",
        "AL",
        "GA",
        "KY",
        "NC",
        "NFL",
        "PR",
        "SC",
        "SFL",
        "TN",
        "VA",
        "VI",
        "WCF",
        "AR",
        "LA",
        "MS",
        "NM",
        "NTX",
        "OK",
        "STX",
        "WTX",
        "EB",
        "LAX",
        "ORG",
        "PAC",
        "SB",
        "SCV",
        "SDG",
        "SF",
        "SJV",
        "SV",
        "AK",
        "AZ",
        "EWA",
        "ID",
        "MT",
        "NV",
        "OR",
        "UT",
        "WWA",
        "WY",
        "MI",
        "OH",
        "WV",
        "IL",
        "IN",
        "WI",
        "AB",
        "BC",
        "GH",
        "MB",
        "NB",
        "NL",
        "NS",
        "ONE",
        "ONN",
        "ONS",
        "PE",
        "QC",
        "SK",
        "TER",
    )
)

# The sections as a SQL list, for the multiplier key.
_SECTIONS_SQL = ",".join(f"'{sect}'" for sect in sorted(ARRL_SECTIONS))


class Contest(ContestBase):
    """ARRL Sweepstakes, Phone."""

    DisplayName = "ARRL Sweepstakes Phone"
    CabrilloName = "ARRL-SS-SSB"
    Mode = "SSB"
    DupeType = 1  # once per contest
    EXCHANGE_HINT = "Prec Call Check Section"
    SOAPBOX_HINT = """For the Run Exchange macro I’d put:
{HISCALL} {SENTNR} {EXCH}

See the Contest Specific Notes section of the manual for more info.
"""
    SendsRTCScore = True
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The four fields are the RSTs, the sent serial and the received exchange.
    FrameText = ("SNT", "SentNR", "sn prec ck sec")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Serial Number Precident Check Section",
    )
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "CK",
        "Prec",
        "Sect",
        "M1",
        "PTS",
    ]
    # The exchange is "sn prec ck sec", whose spaces are significant.
    advance_on_space = [True, True, True, False, False]
    # Each ARRL/RAC section once for the whole contest; a "DX" is not a section
    # and is not a multiplier.
    NumMults = 1
    Multiplier1Name = "Sect"
    MultSqlString = "Sect"
    IsMult1Per = 4

    def reset_label(self):
        """Put the exchange label back after parse_exchange() replaced it."""
        self.parent.exch_label.setText(
            QtWidgets.QApplication.translate("ContestPlugin", "sn prec ck sec")
        )

    def parse_exchange(self):
        """Split the received "sn prec ck sec" into its parts.

        The check and the section can arrive glued to the serial and the
        precedence ("12A78CT"), so a token with letters is split at the first
        letter.
        """
        parent = self.parent
        exchange = parent.other_2.text().upper()
        sn = prec = ck = sec = ""
        call = parent.callsign.text()

        for tokens in exchange.split():
            if tokens.isdigit():
                if sn == "":
                    sn = tokens
                else:
                    ck = tokens
                continue
            if tokens.isalpha():
                if len(tokens) == 1:
                    prec = tokens
                else:
                    sec = tokens
                continue
            if tokens.isalnum():
                if tokens[:1].isalpha():
                    call = tokens
                    continue
                text = numb = ""
                for index, char in enumerate(tokens):
                    if char.isalpha():
                        text = tokens[index:]
                        numb = tokens[:index]
                        break
                if len(text) == 1:
                    prec = text
                    sn = numb
                else:
                    sec = text
                    ck = numb
        parent.exch_label.setText(f"sn:{sn} p:{prec} cl:{call} ck:{ck} sec:{sec}")
        return (sn, prec, ck, sec, call)

    def points(self):
        """2 points, but only between W/VE stations (rule 2.1)."""
        if self.parent.contact_is_dupe > 0:
            return 0
        if str(self.parent.contact.get("Sect", "")).upper() not in ARRL_SECTIONS:
            return 0
        return 2

    def mult_value(self, slot, contact):
        """The section, when it is a real ARRL/RAC one."""
        sect = str(contact.get("Sect", "")).upper()
        return sect if sect in ARRL_SECTIONS else None

    def mult_sql(self, slot):
        """The section as SQL, over the real sections only."""
        return f"CASE WHEN upper(Sect) IN ({_SECTIONS_SQL}) THEN Sect END"

    def set_contact_vars(self):
        """The exchange, parsed into its parts, and the multiplier."""
        parent = self.parent
        sn, prec, ck, sec, call = self.parse_exchange()
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = sn
        parent.contact["Prec"] = prec
        parent.contact["CK"] = ck
        parent.contact["Sect"] = sec
        parent.contact["Call"] = call
        self.mark_multipliers()

    def prefill(self):
        """Fill the sent serial."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def cabrillo_qso_line(self, contact):
        """The Sweepstakes line: the operator's own exchange, then the received.

        The base's line sends and receives a serial; here the sent exchange is
        the operator's precedence/check/section (with their call removed, since
        it is already in the ``StationPrefix`` column) and the received one is
        the serial, precedence, check and section.
        """
        parent = self.parent
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        station_prefix = contact.get("StationPrefix", "")
        sent_exch = parent.contest_settings.get("SentExchange", "").upper()
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{station_prefix.ljust(13)} "
            f"{str(contact.get('SentNr', '')).zfill(4)} "
            f"{sent_exch.replace(' ' + station_prefix, '')} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).zfill(4)} "
            f"{contact.get('Prec', '')} "
            f"{str(contact.get('CK', '')).zfill(2)} "
            f"{contact.get('Sect', '')}"
        )
