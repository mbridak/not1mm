"""TA VHF UHF Contest

Find rules at: https://trac.org.tr/tr/ta-vhf-uhf-contest-2025-english

50, 144 and 432 MHz, once per band and mode.  The exchange is a serial number
and a locator, and a contact scores one point per kilometre between the two
stations, multiplied by the band (50 MHz x1, 144 MHz x2, 432 MHz x3) and by the
mode (FM x1, SSB x2, CW x3).  There are no multipliers: the score is the sum of
the contacts.  The log is EDI.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import band_mhz_of, distance
from not1mm.lib.plugin_common import gen_edi


class Contest(ContestBase):
    """TA VHF UHF Contest."""

    DisplayName = "TA VHF UHF"
    CabrilloName = "TA-VHF-UHF"
    Mode = "BOTH"
    EXCHANGE_HINT = "# + 6char grid"
    DupeType = 3  # work each band/mode once
    UsesESM = False  # the module never drove the ESM state machine
    WritesEDI = True
    Bands = (50, 144, 432)
    DefaultContestExchange = "#"
    # The received exchange is "# grid", so a space is part of it.
    advance_on_space = [True, True, True, True, False]
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "Exchange1",
        "PTS",
    ]
    FrameText = ("SNT", "SNTNR", "RCV NR + GRID")
    AccessibleNames = ("", "", "", "")

    def interface(self):
        """The reports are fixed at 59 and cannot be typed."""
        super().interface()
        parent = self.parent
        parent.sent.setText("59")
        parent.receive.setText("59")
        parent.sent.setReadOnly(True)
        parent.receive.setReadOnly(True)

    def parse_exchange(self):
        """Split the typed exchange into the serial and the 6-character grid."""
        exchange = self.parent.other_2.text().upper().split()
        sn = ""
        grid = ""
        for token in exchange:
            if token.isdigit() and sn == "":
                sn = token
            elif len(token) == 6 and token.isalnum():
                grid = token
        return sn, grid

    def set_contact_vars(self):
        """The typed "# grid" is split, and the sent serial advances."""
        parent = self.parent
        sn, grid = self.parse_exchange()
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = sn
        parent.contact["Exchange1"] = grid
        parent.contact["SentNr"] = parent.other_1.text()
        try:
            next_sn = int(parent.current_sn) + 1
            parent.other_1.setText(str(next_sn).zfill(3))
        except (TypeError, ValueError):
            ...

    def prefill(self):
        """The sent exchange is the running serial, not the setup's text."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if parent.other_1.text() == "":
            parent.other_1.setText(serial_nr)

    def points(self):
        """The distance in kilometres times the band and mode multipliers.

        Points are one per kilometre on 6m, two on 2m and three on 70cm, and
        the mode multiplies that again: FM x1, SSB x2, CW x3.  The score is the
        sum of the contacts.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        their_grid = parent.contact.get("Exchange1", "")
        kilometers = distance(parent.station.get("GridSquare", ""), their_grid)

        # The band column holds a float (144.0), so the lookup is on the
        # number: comparing it to "144" as a string never matched.
        band_mult = {
            50.0: 1,
            144.0: 2,
            432.0: 3,
        }.get(band_mhz_of(parent.contact.get("Band", 0)), 1)

        # And the mode multiplier is FM x1, SSB x2, CW x3 (rule 6).
        mode_mult = {"FM": 1, "SSB": 2, "CW": 3}.get(
            str(parent.contact.get("Mode", "")).upper(), 1
        )

        return max(1, int(kilometers * band_mult * mode_mult))

    def edi(self):
        """Write the EDI log the sponsor wants."""
        parent = self.parent
        value = parent.contest_settings.get("StartDate", "")
        start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
        gen_edi(
            parent,
            self.CabrilloName,
            "TA 50_144_430 Contest",
            start_date,
            start_date,
        )
