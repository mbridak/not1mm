"""ARI International DX Contest

Find rules at: https://www.ari.it/

Phone, CW and RTTY, 80/40/20/15/10m, 12:00 UTC Saturday to 12:00 UTC Sunday in
May.

    Exchange:    Italian stations send RS(T) + province, others RS(T) + serial
    Work:        once per band and mode
    QSO points:  0 with the same country, 1 within a continent, 3 across
                 continents, and 10 for a station in I/IS/IT9
    Multipliers: each Italian province, and each DXCC country except Italy,
                 once per band
    Cabrillo:    ARI-DX

Both the points and the multipliers depend on which side of the contest the
operator is on, so ``points()`` and ``mult_value()`` stay methods; the counting
and the score come from the base.  A province is the received exchange only
when it is a code rather than a serial number, which is what ``NR`` being text
rather than an integer means in the database.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)

# The Italian primary prefixes: Italy, Sardinia (IS) and Sicily (IT9).
_ITALIAN_PREFIXES = ("I", "IS", "IT9")


class Contest(ContestBase):
    """ARI International DX."""

    DisplayName = "ARI International DX"
    CabrilloName = "ARI-DX"
    Mode = "BOTH"
    DupeType = 3  # once per band and mode
    EXCHANGE_HINT = "Prov or '#'"
    DefaultContestExchange = "#"
    ADIFContestID = "ARI-DX"
    SupportsFT8 = True
    Bands = (3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "PTS",
    ]
    FrameText = ("SNT", "", "Prov or SN")
    AccessibleNames = ("RST Sent", "", "", "Province or Serial Number")
    # An Italian province once per band, and a DXCC country (Italy excepted)
    # once per band.  Both keys are conditional, so they are methods.
    NumMults = 2
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1

    def _entity(self, call):
        """The cty.dat entry for *call*, or None."""
        result = self.parent.cty_lookup(call)
        if result is None:
            return None
        return result.get(next(iter(result)))

    def points(self):
        """Points for the contact being logged (rule 8)."""
        if self.parent.contact_is_dupe > 0:
            return 0

        me = self._entity(self.parent.station.get("Call", "")) or {}
        them = self._entity(self.parent.contact.get("Call", "")) or {}
        my_country = me.get("primary_pfx", "")
        their_country = them.get("primary_pfx", "")

        # Two Italian stations may not work each other.  Sardinia is IS, not
        # IS0, so it is matched here as well.
        if my_country in _ITALIAN_PREFIXES and their_country in _ITALIAN_PREFIXES:
            return 0
        if my_country == their_country:
            return 0
        if their_country in _ITALIAN_PREFIXES:
            return 10
        if me.get("continent", "") != them.get("continent", ""):
            return 3
        return 1

    def mult_value(self, slot, contact):
        """The key: the province (a code, not a serial) or the country.

        Works on a logged contact, on the one being typed and on a bandmap
        spot alike, so a province is only a province when it is not a serial
        number, and Italy is counted by its provinces rather than as a country.
        """
        if slot == 1:
            nr = contact.get("NR")
            if isinstance(nr, str) and nr and not nr.isdigit():
                return nr
            return None
        if slot == 2:
            country = contact.get("CountryPrefix", "")
            return country if country and country not in _ITALIAN_PREFIXES else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same two keys as SQL, for counting the log.

        ``NR`` is an INTEGER column, so a province is stored as text and a
        serial number as an integer: the two are told apart by ``typeof``.
        """
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' AND NR != '' THEN NR END"
        if slot == 2:
            return (
                "CASE WHEN CountryPrefix NOT IN ('I', 'IS', 'IT9') "
                "THEN CountryPrefix END"
            )
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The exchange, and the multipliers the contact is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        self.mark_multipliers()

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP.

        WSJT-X sends ``STX_STRING``/``STATE`` and fldigi ``STX``/``SRX``; both
        end up in the usual fields and the contact is saved without the
        operator touching anything.
        """
        parent = self.parent
        logger.debug("%s", f"{packet=}")
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = packet.get("RST_SENT", "599")
        parent.contact["RCV"] = packet.get("RST_RCVD", "599")

        sent_string = packet.get("STX_STRING", "")
        if sent_string != "":
            parent.contact["SentNr"] = sent_string
            parent.other_1.setText(str(sent_string))
        else:
            parent.contact["SentNr"] = packet.get("STX", "000")
            parent.other_1.setText(str(packet.get("STX", "000")))

        rx_string = packet.get("STATE", "")
        if rx_string != "":
            parent.contact["NR"] = rx_string
            parent.other_2.setText(str(rx_string))
        else:
            parent.contact["NR"] = packet.get("SRX", "000")
            parent.other_2.setText(str(packet.get("SRX", "000")))

        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        logger.debug("%s", f"{parent.contact=}")
        parent.save_contact()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Sect', '')}"
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
                parent.other_2.setText(f"{result.get('Sect', '')}")
