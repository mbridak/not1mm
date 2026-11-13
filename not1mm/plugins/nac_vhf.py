"""NAC VHF

Find rules at: https://www.darc.de/der-club/referate/conteste/ukw/

The Nordic Activity Contest on 50 MHz and above, once per contest.  A contact
scores one point per kilometre between the two stations, multiplied by the
GHz factor of the band on 2.3 GHz and above, and 500 points more for the first
contact in each large (four-character) square.  The multiplier display is the
number of large squares worked, but the score is the sum of the points, so it
is not multiplied by them.  The log is EDI.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from PyQt6 import QtWidgets

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import distance
from not1mm.lib.plugin_common import gen_edi

# GHz multiplier for the microwave section (2.3 GHz and above)
# Keys match the not1mm BandCategory dropdown values (new_contest.ui).
GHZ_MULT = {
    "2.3G": 2,
    "3.4G": 3,
    "5.7G": 4,
    "10G": 5,
    "24G": 6,
    "47G": 7,
}

LARGE_SQUARE_BONUS = 500


def large_square(grid):
    """Return the 4-character large square (e.g. JO49) from a 6-character locator."""
    if not grid or len(grid) < 4:
        return ""
    return grid[:4].upper()


def bandinMHz(band):
    switch = {
        "ALL": "ALL",
        "160M": "1,8 MHz",
        "80M": "3,5 MHz",
        "40M": "7 MHz",
        "20M": "14 MHz",
        "15M": "21 MHz",
        "10M": "28 MHz",
        "6M": "50 MHz",
        "2M": "144 MHz",
        "222": "222 MHz",
        "432": "432 MHz",
        "902": "902 MHz",
        "1.2G": "1,3 GHz",
        "2.3G": "2,3 GHz",
        "3.4G": "3,4 GHz",
        "5.7G": "5,7 GHz",
        "10G": "10 GHz",
        "24G": "24 GHz",
        "47G": "47 GHz",
        "75G": "75 GHz",
        "119G": "119 GHz",
        "142G": "142 GHz",
        "241G": "241 GHz",
    }
    # For any band not explicitly mapped (e.g. ALL, LIGHT, VHF-3-BAND,
    # VHF-FM-ONLY) fall back to the band string itself rather than
    # emitting a bogus literal.
    return switch.get(band, band or "ALL")


def ghz_multiplier(parent):
    """Return the GHZ multiplier for the current band (1 for bands <= 1296 MHz)."""
    return GHZ_MULT.get(str(parent.contest_settings.get("BandCategory", "")), 1)


def bonus_for_square(parent):
    """Return 500 if the current QSO's large square is new in this contest, else 0.

    A large square is 'new' if it does not appear in any already-logged contact.
    """
    _grid = parent.contact.get("Exchange1", "").upper()
    _square = large_square(_grid)
    if not _square:
        return 0

    existing = parent.database.exec_sql(
        "select count(*) as cnt from dxlog where ContestNR = ? and Exchange1 like ?;",
        (parent.database.current_contest, f"{_square}%"),
    )
    if existing and int(existing.get("cnt", 0)) > 0:
        return 0
    return LARGE_SQUARE_BONUS


class Contest(ContestBase):
    """NAC VHF."""

    DisplayName = "NAC VHF"
    CabrilloName = "NAC"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# + 6char grid"
    # Rule 4: "Each station counts only once per test."
    DupeType = 1
    WritesEDI = True
    # 50 MHz and above; the GHz factor starts at 2.3 GHz (see GHZ_MULT).
    Bands = (50, 144, 222, 432, 902, 1296, 2300, 3300, 5650, 10000, 24000, 47000)
    # The received exchange is "# grid", so a space is part of it; the label
    # follows what was typed (see parse_exchange).
    advance_on_space = [True, True, True, True, False]
    call_parse_exchange_on_edit = True
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
    FrameText = ("SNT", "SentNR", "# Grid")
    AccessibleNames = ("RST Sent", "", "Sent Number", "Gridsquare")

    def reset_label(self):
        """Put the exchange label back after the field is cleared."""
        self.parent.exch_label.setText(
            QtWidgets.QApplication.translate("ContestPlugin", "# Grid")
        )

    def parse_exchange(self):
        """Parse the typed exchange into the serial and the 6-character grid."""
        parent = self.parent
        exchange = parent.other_2.text().upper()
        sn = ""
        grid = ""
        for token in exchange.split():
            if token.isdigit():
                if sn == "":
                    sn = token
                continue
            if token.isalnum():
                if len(token) == 6:
                    grid = token
                continue
        parent.exch_label.setText(f"Sn:{sn} Grid:{grid}")
        return (sn, grid)

    def set_contact_vars(self):
        """The typed "# grid" is split into the serial and the locator."""
        parent = self.parent
        sn, grid = self.parse_exchange()
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = sn
        parent.contact["Exchange1"] = grid

    def points(self):
        """One point per kilometre, scaled by the GHz factor, plus square bonus.

        Rule 5: on bands up to and including 1296 MHz a contact is one point
        per kilometre, on 2.3 GHz and above one point per kilometre times the
        GHz multiplier, and the first contact in each large square is worth
        500 more.
        """
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0

        their_grid = str(parent.contact.get("Exchange1", "") or "").upper()
        points = 0
        if their_grid:
            points = distance(parent.station.get("GridSquare", ""), their_grid)
        points = int(points * ghz_multiplier(parent))
        points += bonus_for_square(parent)
        return points

    def show_mults(self):
        """The number of distinct large squares worked.

        There is no multiplied score here -- the points are the sum of the
        contacts -- so this is only what the score display shows.
        """
        squares = set()
        for contact in self.parent.database.fetch_all_contacts_asc():
            square = large_square(contact.get("Exchange1", ""))
            if square:
                squares.add(square)
        return len(squares)

    def cabrillo_qso_line(self, contact):
        """The locator is a field of its own in this contest's log."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '')).upper().ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '')).ljust(6)} "
            f"{str(contact.get('Exchange1', '')).ljust(6)}"
        )

    def recalculate_mults(self):
        """Rescore the log: the 500 point bonus goes to the first contact only.

        The score is the sum of the ``Points`` column, so the distance and the
        square bonus are both worked out again, in log order, or a re-scored or
        imported log would keep whatever it was written with.
        """
        parent = self.parent
        squares_worked = set()
        for contact in parent.database.fetch_all_contacts_asc():
            their_grid = str(contact.get("Exchange1", "") or "").upper()
            points = 0
            if their_grid:
                points = distance(parent.station.get("GridSquare", ""), their_grid)
            points = int(points * ghz_multiplier(parent))

            square = large_square(their_grid)
            if square and square not in squares_worked:
                points += LARGE_SQUARE_BONUS
                squares_worked.add(square)

            contact["Points"] = points
            parent.database.change_contact(contact)

    def edi(self):
        """Write the EDI log the sponsor wants."""
        parent = self.parent
        value = parent.contest_settings.get("StartDate", "")
        start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
        gen_edi(
            parent,
            self.CabrilloName,
            "NAC",
            start_date,
            start_date,
        )

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        Both exchange fields -- the sent locator and the received "# grid" --
        are needed before the contact can be logged.
        """
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
            parent.F1,
            parent.F2,
            parent.F3,
            parent.F4,
            parent.F5,
            parent.F6,
            parent.F7,
            parent.F8,
            parent.F9,
            parent.F10,
            parent.F11,
            parent.F12,
        ):
            parent.restore_button_color(a_button)

        buttons_to_send = []
        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
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
        """Prefill the sent locator from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Exch1', '')}")
