import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import distance
from not1mm.lib.plugin_common import gen_adif, gen_edi, get_points, imp_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

assert imp_adif

EXCHANGE_HINT = "# + 6char grid"

name = "NAC VHF"
mode = "BOTH"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 5, 6, 11, 15]
columns = [
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
cabrillo_name = "NAC"

advance_on_space = [True, True, True, True, False]
call_parse_exchange_on_edit = True

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
# Rule 4: "Each station counts only once per test."
dupe_type = 1

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


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.other_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "SentNR")
    )
    self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "# Grid"))
    self.field4.setAccessibleName("Gridsquare")


def reset_label(self):
    """reset label after field cleared"""
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "# Grid"))


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Contest Specific"""
    sn, grid = parse_exchange(self)
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = sn
    self.contact["Exchange1"] = grid


def parse_exchange(self):
    """Parse exchange..."""
    exchange = self.other_2.text()
    exchange = exchange.upper()
    sn = ""
    grid = ""
    for tokens in exchange.split():
        if tokens.isdigit():
            if sn == "":
                sn = tokens
            continue
        elif tokens.isalnum():
            if len(tokens) == 6:
                grid = tokens
            continue
    label = f"Sn:{sn} Grid:{grid}"
    self.exch_label.setText(label)
    return (sn, grid)


def predupe(self):
    """prefill his exchange with last known values"""


def prefill(self):
    """Fill SentNR"""
    exch = str(self.contest_settings.get("SentExchange", 0))
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exch.replace("#", serial_nr))


def large_square(grid):
    """Return the 4-character large square (e.g. JO49) from a 6-character locator."""
    if not grid or len(grid) < 4:
        return ""
    return grid[:4].upper()


def ghz_multiplier(self):
    """Return the GHZ multiplier for the current band (1 for bands <= 1296 MHz)."""
    return GHZ_MULT.get(str(self.contest_settings.get("BandCategory", "")), 1)


def bonus_for_square(self):
    """Return 500 if the current QSO's large square is new in this contest, else 0.

    A large square is 'new' if it does not appear in any already-logged contact.
    """
    _grid = self.contact.get("Exchange1", "").upper()
    _square = large_square(_grid)
    if not _square:
        return 0

    existing = self.database.exec_sql(
        "select count(*) as cnt from dxlog where ContestNR = ? and Exchange1 like ?;",
        (self.database.current_contest, f"{_square}%"),
    )
    if existing and int(existing.get("cnt", 0)) > 0:
        return 0
    return LARGE_SQUARE_BONUS


def points(self):
    """Calc point
    Rule 5:
      Bands up to and including 1296 MHz:
        1 point per km + 500 points for each new large square.
      2.3 GHz and above:
        1 point per km x GHz multiplier + 500 points for each new large square.
    """

    if self.contact_is_dupe > 0:
        return 0

    _their_grid = self.contact.get("Exchange1", "").upper()
    _points = 0
    if _their_grid:
        _points = distance(self.station.get("GridSquare", ""), _their_grid)

    _points = int(_points * ghz_multiplier(self))

    _points += bonus_for_square(self)

    return _points


def show_mults(self, rtc=None):
    """Return display string for mults (count of distinct large squares worked)"""
    all_contacts = self.database.fetch_all_contacts_asc()
    squares = set()
    for contact in all_contacts:
        sq = large_square(contact.get("Exchange1", ""))
        if sq:
            squares.add(sq)
    return len(squares)


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score (sum of all points)"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)
        return contest_points
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "NAC Contest")


def edi(self):
    value = self.contest_settings.get("StartDate", "")
    start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
    gen_edi(
        self,
        cabrillo_name,
        "NAC",
        start_date,
        start_date,
    )


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


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
    # https://www.cqwpx.com/cabrillo.htm
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now().astimezone()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper().replace('/', '-')}_{cabrillo_name}_{date_time}.log"
    )
    logger.debug("%s", filename)
    log = self.database.fetch_all_contacts_asc()
    try:
        with open(filename, "w", encoding=file_encoding, newline="") as file_descriptor:
            output_cabrillo_line(
                "START-OF-LOG: 3.0",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CREATED-BY: Not1MM v{__version__}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CONTEST: {cabrillo_name}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            if self.station.get("Club", ""):
                output_cabrillo_line(
                    f"CLUB: {self.station.get('Club', '').upper()}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"CALLSIGN: {self.station.get('Call', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"LOCATION: {self.station.get('ARRLSection', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-OPERATOR: {self.contest_settings.get('OperatorCategory', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-ASSISTED: {self.contest_settings.get('AssistedCategory', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-BAND: {self.contest_settings.get('BandCategory', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            mode = self.contest_settings.get("ModeCategory", "")
            if mode in ["SSB+CW", "SSB+CW+DIGITAL"]:
                mode = "MIXED"
            output_cabrillo_line(
                f"CATEGORY-MODE: {mode}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-TRANSMITTER: {self.contest_settings.get('TransmitterCategory', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            if self.contest_settings.get("OverlayCategory", "") != "N/A":
                output_cabrillo_line(
                    f"CATEGORY-OVERLAY: {self.contest_settings.get('OverlayCategory', '')}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"GRID-LOCATOR: {self.station.get('GridSquare', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-POWER: {self.contest_settings.get('PowerCategory', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )

            output_cabrillo_line(
                f"CLAIMED-SCORE: {calc_score(self)}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            ops = ""
            list_of_ops = self.database.get_ops()
            for op in list_of_ops:
                ops += f"{op.get('Operator', '')}, "
            if self.station.get("Call", "") not in ops:
                ops += f"@{self.station.get('Call', '')}"
            else:
                ops = ops.rstrip(", ")
            output_cabrillo_line(
                f"OPERATORS: {ops}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"NAME: {self.station.get('Name', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS: {self.station.get('Street1', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-CITY: {self.station.get('City', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-STATE-PROVINCE: {self.station.get('State', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-POSTALCODE: {self.station.get('Zip', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS-COUNTRY: {self.station.get('Country', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"EMAIL: {self.station.get('Email', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode in ("CW-U", "CW-L", "CW-R", "CWR"):
                    themode = "CW"
                if themode == "LSB" or themode == "USB":
                    themode = "PH"
                frequency = str(round(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '')).upper().ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '')).ljust(6)} "
                    f"{str(contact.get('Exchange1', '')).ljust(6)}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line("END-OF-LOG:", "\r\n", file_descriptor, file_encoding)
        self.show_message_box(f"Cabrillo saved to: {filename}")
    except OSError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso.

    Iterates contacts in chronological order so the 500 point new-large-square
    bonus is awarded only to the first QSO in each large square.
    """
    all_contacts = self.database.fetch_all_contacts_asc()
    squares_worked = set()
    for contact in all_contacts:
        _their_grid = contact.get("Exchange1", "").upper()
        _points = 0
        if _their_grid:
            _points = distance(self.station.get("GridSquare", ""), _their_grid)
        _points = int(_points * ghz_multiplier(self))

        _square = large_square(_their_grid)
        if _square and _square not in squares_worked:
            _points += LARGE_SQUARE_BONUS
            squares_worked.add(_square)

        contact["Points"] = _points
        self.database.change_contact(contact)


def process_esm(self, new_focused_widget=None, with_enter=False):
    """ESM State Machine"""

    # self.pref["run_state"]

    # -----===== Assigned F-Keys =====-----
    # self.esm_dict["CQ"]
    # self.esm_dict["EXCH"]
    # self.esm_dict["QRZ"]
    # self.esm_dict["AGN"]
    # self.esm_dict["HISCALL"]
    # self.esm_dict["MYCALL"]
    # self.esm_dict["QSOB4"]

    # ----==== text fields ====----
    # self.callsign
    # self.sent
    # self.receive
    # self.other_1
    # self.other_2

    if new_focused_widget is not None:
        self.current_widget = self.inputs_dict.get(new_focused_widget)

    for a_button in [
        self.F1,
        self.F2,
        self.F3,
        self.F4,
        self.F5,
        self.F6,
        self.F7,
        self.F8,
        self.F9,
        self.F10,
        self.F11,
        self.F12,
    ]:
        self.restore_button_color(a_button)

    buttons_to_send = []

    if self.pref.get("run_state"):
        if self.current_widget == "callsign":
            if len(self.callsign.text()) < 3:
                self.make_button_green(self.esm_dict["CQ"])
                buttons_to_send.append(self.esm_dict["CQ"])
            elif len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["HISCALL"])
                buttons_to_send.append(self.esm_dict["EXCH"])

        elif self.current_widget in ["other_1", "other_2"]:
            if self.other_2.text() == "" or self.other_1.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            else:
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)
    else:
        if self.current_widget == "callsign":
            if len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["MYCALL"])
                buttons_to_send.append(self.esm_dict["MYCALL"])

        elif self.current_widget in ["other_1", "other_2"]:
            if self.other_2.text() == "" or self.other_1.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            else:
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('Exch1', '')}, {result.get('UserText', '...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText', '')}")
        if self.other_1.text() == "":
            self.other_1.setText(f"{result.get('Exch1', '')}")


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["state"], mults["wpxprefix"] = show_mults(self, rtc=True)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
