"""UKEI-DX contest plugin

Find rules at: https://www.ukeicc.com/dx-contest-rules.php

80-10m, CW and SSB, once per band.  Points depend on which of the three groups
the operator is in (UK/EI, the rest of Europe, DX) and on the band, and a UK/EI
entrant's contacts score double between 0100z and 0459z.  Two multipliers, each
counted per band: every DXCC country outside the UK/EI entities, and the two
character district at the end of the received exchange.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of
from not1mm.lib.plugin_common import contest_time

# The UK/EI entities, from cty.dat's primary prefixes.
UKEI_PREFIXES = ("G", "GD", "GJ", "GM", "GI", "GW", "GU", "EI")

# The UK/EI countries are counted by their districts, not as countries, so the
# first multiplier excludes them.
_NOT_A_COUNTRY = "'EI', 'G', 'GD', 'GI', 'GJ', 'GM', 'GU', 'GW'"


def _sent_serial(value) -> str:
    """The sent serial and district, zero-padded; ``000 --`` when absent."""
    parts = str(value).upper().split()
    if not parts:
        return "000 --"
    if len(parts) == 2:
        return parts[0].zfill(3) + " " + parts[1]
    return parts[0].zfill(3) + " --"


def _received_serial(value) -> str:
    """The received serial and district, zero-padded.

    A single token that ends in a two-letter district (``002G``) is split there;
    anything else is a bare serial and gets the ``--`` placeholder.
    """
    parts = str(value).upper().split()
    if not parts:
        return "000 --"
    if len(parts) == 2:
        return parts[0].zfill(3) + " " + parts[1]
    if parts[0][-2:].isalpha():
        return parts[0][:-2].zfill(3) + " " + parts[0][-2:]
    return parts[0].zfill(3) + " --"


class Contest(ContestBase):
    """UKEI-DX."""

    DisplayName = "UKEI-DX"
    CabrilloName = "UKEI-DX"
    Mode = "BOTH"
    DupeType = 2  # once per band
    EXCHANGE_HINT = "# or # And Dist"
    SOAPBOX_HINT = """For the Run exchange macro I’d put ’{SNT} # {EXCH}’"""
    SendsRTCScore = True
    DefaultContestExchange = "#"
    Bands = (3.5, 7, 14, 21, 28)
    # The district is part of the received exchange and its space is
    # significant ("002 G"), so neither exchange field strips one.
    advance_on_space = [True, True, True, False, False]
    FrameText = ("SNT", "Sent Nr", "# and Dist")
    AccessibleNames = ("RST Sent", "Sent Number", "", "Number and District")
    # Each country outside the UK/EI entities, and each UK/EI district, on each
    # band.
    NumMults = 2
    Multiplier1Name = "Country"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    Multiplier2Name = "District"
    MultSqlString2 = "NR"
    IsMult2Per = 1

    def points(self):
        """The three-sided ladder, doubled inside the 0100-0459z window.

        UK/EI stations score every contact; a European station scores UK/EI
        best and DX least; a DX station scores UK/EI best and its own
        continent least.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        myprimary_pfx = ""
        mycontinent = ""
        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            myprimary_pfx = item.get("primary_pfx", "")
            mycontinent = item.get("continent", "")

        hisprimary_pfx = ""
        hiscontinent = ""
        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            hisprimary_pfx = item.get("primary_pfx", "")
            hiscontinent = item.get("continent", "")

        # Note: for UK/EI stations only, all QSOs score double between the
        # hours of 0100z and 0459z.  The contact's own time is used so that a
        # re-scored or imported log is judged against the clock it was logged
        # on, not the wall clock.
        now = contest_time(parent)
        ct = now.hour * 100 + now.minute
        double_window = 100 <= ct <= 459
        band = band_mhz_of(parent.contact.get("Band"))

        # UK/EI stations
        if myprimary_pfx in UKEI_PREFIXES:
            if hiscontinent == "EU":
                if band in (3.5, 7.0):
                    return 4 + (4 * double_window)
                return 2 + (2 * double_window)
            if band in (3.5, 7.0):
                return 8 + (8 * double_window)
            return 4 + (4 * double_window)

        # European stations
        if mycontinent == "EU":
            if hisprimary_pfx in UKEI_PREFIXES:
                if band in (3.5, 7.0):
                    return 4
                return 2
            elif hiscontinent == "EU":
                if band in (3.5, 7.0):
                    return 2
                return 1
            if band in (3.5, 7.0):
                return 4
            return 2

        # DX (outside Europe)
        if mycontinent != "EU":
            if hisprimary_pfx in UKEI_PREFIXES:
                if band in (3.5, 7.0):
                    return 8
                return 4
            elif hiscontinent == "EU":
                if band in (3.5, 7.0):
                    return 4
                return 2
            if band in (3.5, 7.0):
                return 2
            return 1

        return 0

    def mult_sql(self, slot: int):
        """Rule 7.2's two keys: the country, and the two-letter district.

        The country half skips the UK/EI entities (their districts count
        instead) and an empty prefix, and the district half reads only a text
        ``NR`` -- a numeric one is a serial, not a district.
        """
        if slot == 1:
            return (
                f"CASE WHEN CountryPrefix NOT IN ({_NOT_A_COUNTRY}) "
                "AND CountryPrefix <> '' THEN CountryPrefix END"
            )
        if slot == 2:
            return "CASE WHEN typeof(NR) = 'text' THEN SUBSTR(NR, LENGTH(NR) - 1) END"
        return super().mult_sql(slot)

    def mult_value(self, slot: int, contact):
        """The same two keys in Python, for the live "new mult" question."""
        if slot == 1:
            prefix = str(contact.get("CountryPrefix", "") or "")
            if not prefix or prefix in UKEI_PREFIXES:
                return None
            return prefix
        if slot == 2:
            nr = contact.get("NR", "")
            if isinstance(nr, str) and nr:
                return nr[-2:]
            return None
        return super().mult_value(slot, contact)

    def get_mults(self):
        """The score page is told nothing, as the module told it."""
        return {}

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplierN``."""

    def set_contact_vars(self):
        """The exchange; the received serial and district are upper-cased."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def cabrillo_qso_line(self, contact):
        """The UKEI line: the serial and district, both zero-padded."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} "
            f"{self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{_sent_serial(contact.get('SentNr', ''))} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{_received_serial(contact.get('NR', ''))}"
        )

    def populate_history_info_line(self):
        """Show the history info for the typed call."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Exch1', '')}, "
                f"{result.get('UserText', '...')}"
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
                parent.other_2.setText(f"{result.get('Exch1', '')}")
