"""RSGB-IOTA

Find rules at: https://www.rsgbcc.org/hf/rules/2025/riota.shtml

80m to 10m, CW and SSB, once per band and mode.  The exchange is RST, a serial
and, from an island station, its IOTA reference.  An island station scores 5
against a world station or an island in the same group and 15 against another
island; a world station scores 2 against another world station and 15 against
an island.  Each IOTA reference counts once per band and mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


def convert_iota_number(iota: str) -> str:
    """Convert an IOTA reference string to its Cabrillo form."""
    if len(iota) >= 3 and iota[:2].isalpha and iota[2:].isdigit():
        return f"{iota[:2].upper()}-{iota[2:].zfill(3)}"

    return iota


class Contest(ContestBase):
    """RSGB-IOTA."""

    DisplayName = "RSGB-IOTA"
    CabrilloName = "RSGB-IOTA"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# or # And IOTA number"
    SOAPBOX_HINT = """For the Run exchange macro I’d put ’{SNT} {SENTNR}’"""
    DupeType = 3  # work each band and mode once
    Bands = (3.5, 7, 14, 21, 28)
    FrameText = ("SNT", "Sent Nr", "# and Dist")
    AccessibleNames = ("RST Sent", "", "Sent Number", "Number and District")
    # The sent and received exchanges both hold a serial and an IOTA reference
    # separated by a space, so the space in either field is part of the text.
    advance_on_space = [True, True, True, False, False]
    SendsRTCScore = True
    # Each IOTA reference once per band and mode.
    NumMults = 1
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 3

    def mult_sql(self, slot: int):
        """The IOTA reference, i.e. what follows the space in the exchange."""
        if slot != 1:
            return super().mult_sql(slot)
        return "CASE WHEN INSTR(NR, ' ') THEN SUBSTR(NR, INSTR(NR, ' ') + 1) END"

    def mult_value(self, slot: int, contact):
        """The same IOTA reference as :meth:`mult_sql`, from a row or a spot."""
        if slot != 1:
            return super().mult_value(slot, contact)
        exchange = str(contact.get("NR", "")).upper().split()
        if len(exchange) != 2:
            return None
        return convert_iota_number(exchange[1])

    def set_contact_vars(self):
        """Store the exchange with the IOTA number in its Cabrillo form."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        their_exchange = parent.other_2.text().upper()
        parent.contact["NR"] = convert_iota_number(their_exchange)
        their_exchange = their_exchange.split()
        if len(their_exchange) == 2:
            parent.contact["NR"] = (
                f"{their_exchange[0]} "
                f"{convert_iota_number(their_exchange[1]).replace('-', '')}"
            )
        parent.contact["SentNr"] = parent.other_1.text().upper()

    def prefill(self):
        """Fill the sent exchange: the setup's value, with `#` as the serial."""
        parent = self.parent
        exch = str(parent.contest_settings.get("SentExchange", 0))
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(exch.replace("#", serial_nr))

    def points(self):
        """Island-to-island 15, island-to-world 5, world-to-island 15, rest 2."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        im_island = False
        my_ref = ""
        theyre_island = False
        their_ref = ""

        my_exchange = str(parent.contest_settings.get("SentExchange", 0))
        my_exchange = my_exchange.split()
        if len(my_exchange) == 2:
            im_island = True
            my_ref = convert_iota_number(my_exchange[1])

        their_exchange = parent.other_2.text().upper()
        their_exchange = their_exchange.split()
        if len(their_exchange) == 2:
            theyre_island = True
            their_ref = convert_iota_number(their_exchange[1])

        if im_island:
            if theyre_island:
                if my_ref == their_ref:
                    return 5
                return 15
            return 5
        if theyre_island:
            return 15
        return 2

    def get_mults(self):
        """The real-time score page gets no multiplier rows from this contest."""
        return {}

    def cabrillo_qso_line(self, contact):
        """The four-digit serials, with the IOTA number in its Cabrillo form."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)

        sentnr = str(contact.get("SentNr", "")).upper().split()
        if not sentnr:
            sentnr = "0000 ------"
        elif len(sentnr) == 2:
            sentnr = sentnr[0].zfill(4) + " " + convert_iota_number(sentnr[1])
        else:
            sentnr = sentnr[0].zfill(4) + " ------"

        nr = str(contact.get("NR", "")).upper().split()
        if not nr:
            nr = "0000 ------"
        elif len(nr) == 2:
            nr = nr[0].zfill(4) + " " + convert_iota_number(nr[1])
        elif nr[0][-2:].isalpha():
            nr = nr[0][:-2].zfill(4) + " " + nr[0][-2:]
        else:
            nr = nr[0].zfill(4) + " ------"

        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{sentnr} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{nr}"
        )

    def populate_history_info_line(self):
        """Fill the history line from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Sect', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Populate the exchange field from past QSO information."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
