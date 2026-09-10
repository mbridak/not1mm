"""
IARU Region 1 VHF & Up Contest Plugin

Rules: https://www.iaru-r1.org/wp-content/uploads/2026/09/Rules-IARU-R1-VHF-up-Contests.pdf

Key rules:
  - Exchange: RS(T) + serial number (per band, starting at 001) + 6-char locator
  - Dupe type: once per band (can work same station on different bands)
  - Scoring: floor(distance_km) + 1 for bands up to 10 GHz
  - Millimetre group (24 GHz+): band multiplication factors applied
  - Multiplier: count of distinct large (4-char) grid squares worked
  - Serial numbers restart at 001 per band
  - Log format: EDI (REG1TEST), one file per band
"""

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import distance as ham_distance
from not1mm.lib.plugin_common import gen_adif, gen_edi, imp_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

assert imp_adif

EXCHANGE_HINT = "RS + serial + 6char grid"

name = "IARU R1 VHF"
mode = "BOTH"  # CW SSB BOTH RTTY
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
cabrillo_name = "IARU-R1-VHF"
advance_on_space = [True, True, True, True, False]
dupe_type = 2  # Once per band; same station may be worked on different bands

# Millimetre group band multiplication factors (bands above 10 GHz)
MM_FACTOR = {
    "24G": 1,
    "47G": 2,
    "75G": 3,
    "119G": 4,
    "142G": 8,
    "241G": 10,
}


def init_contest(self):
    """Set up tab order, interface, serial number for current band."""
    logger.debug("IARU R1 VHF init_contest")
    interface(self)
    set_tab_next(self)
    set_tab_prev(self)
    self.next_field = self.other_2


def interface(self):
    """Set up the UI labels and field visibility for this contest."""
    try:
        self.field_1.show()
        self.field_1_label.setText("Sent")
        self.field_2.show()
        self.field_2_label.setText("SntNr")
        self.field_3.show()
        self.field_3_label.setText("rcvd")
        self.field_4.show()
        self.field_4_label.setText("RcvNr")
        self.exch_label.setText(
            QtWidgets.QApplication.translate("ContestPlugin", "# Grid")
        )
        self.OtherLabel1.setText("SentNr")
        self.OtherLabel2.setText("rcvExchange")
        self.populate_history_info_line(self)
    except AttributeError:
        pass


def set_tab_next(self):
    """Set forward tab order."""
    try:
        self.tab_next = {
            self.callsign: self.sent,
            self.sent: self.receive,
            self.receive: self.other_1,
            self.other_2: self.callsign,
            self.other_1: self.other_2,
        }
    except AttributeError:
        pass


def reset_label(self):
    """reset label after field cleared"""
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "# Grid"))


def set_tab_prev(self):
    """Set backward tab order."""
    try:
        self.tab_prev = {
            self.callsign: self.other_2,
            self.sent: self.callsign,
            self.receive: self.sent,
            self.other_2: self.other_1,
            self.other_1: self.receive,
        }
    except AttributeError:
        pass


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


def set_contact_vars(self):
    """Copy UI fields into self.contact for this contest."""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    parsed = parse_exchange(self)
    self.contact["NR"] = parsed[1]
    self.contact["Exchange1"] = parsed[2]


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Set serial number for the current band (next after the highest logged on this band)."""
    try:
        band = str(self.contest_settings.get("BandCategory", ""))
        serial = _next_serial_for_band(self, band)
        self.other_1.setText(f"{serial:03d}")
        self.current_sn = serial
    except AttributeError:
        pass


def _next_serial_for_band(self, band):
    """Return the next serial number for the given band category."""
    band_freq = bandinMHz(band)
    query = "SELECT MAX(CAST(SentNr AS INTEGER)) AS maxsn FROM dxlog WHERE ContestNR = ? AND Band = ?;"
    result = self.database.exec_sql(
        query,
        (self.database.current_contest, band_freq),
    )
    if result and result.get("maxsn") is not None:
        try:
            return int(result["maxsn"]) + 1
        except (TypeError, ValueError):
            pass
    return 1


def distance(my_grid, their_grid):
    """Calculate distance in km between two 6-character locators.
    The distance in km is truncated to an integer and 1 km is added.
    The centre of each locator square is used."""
    if not my_grid or not their_grid or len(my_grid) < 4 or len(their_grid) < 4:
        return 0
    try:
        km = ham_distance(my_grid, their_grid)
        if km is None or km <= 0:
            km = 0
        return int(km) + 1
    except (TypeError, ValueError):
        return 0


def points(self):
    """Calculate points for this contact.
    Bands up to 10 GHz: floor(distance_km) + 1
    Millimetre bands (24 GHz+): (floor(distance_km) + 1) x band factor
    """
    if self.contact_is_dupe > 0:
        return 0
    _their_grid = self.contact.get("Exchange1", "").upper()
    if _their_grid and len(_their_grid) >= 4:
        _points = distance(self.station.get("GridSquare", ""), _their_grid)
    else:
        _points = 0

    band = str(self.contest_settings.get("BandCategory", ""))
    mm_factor = MM_FACTOR.get(band, 1)
    _points = int(_points * mm_factor)

    return _points


def show_mults(self, rtc=None):
    """Return the count of distinct large (4-char) grid squares worked."""
    all_contacts = self.database.fetch_all_contacts_asc()
    squares = set()
    for contact in all_contacts:
        grid = contact.get("Exchange1", "")
        if grid and len(grid) >= 4:
            squares.add(grid[:4].upper())
    return len(squares)


def show_qso(self):
    """Return QSO count."""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score (sum of all Points)."""
    result = self.database.fetch_points()

    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        return int(score)
    return 0


def get_mults(self):
    """Return multiplier dict for RTC XML."""
    return {"state": show_mults(self)}


def just_points(self):
    """Return raw points for RTC XML."""
    return calc_score(self)


def bandinMHz(band):
    """Map band category string to EDI PBand display string."""
    switch = {
        "ALL": "ALL",
        "160M": "1,8 MHz",
        "80M": "3,5 MHz",
        "40M": "7 MHz",
        "20M": "14 MHz",
        "15M": "21 MHz",
        "10M": "28 MHz",
        "6M": "50 MHz",
        "4M": "70 MHz",
        "2M": "145 MHz",
        "432": "435 MHz",
        "1.2G": "1,3 GHz",
        "2.3G": "2,3 GHz",
        "3.4G": "3,4 GHz",
        "5.7G": "5,7 GHz",
        "10G": "10 GHz",
        "24G": "24 GHz",
        "47G": "47 GHz",
        "75G": "76 GHz",
        "119G": "122 GHz",
        "142G": "134 GHz",
        "241G": "245 GHz",
    }
    return switch.get(band, band or "ALL")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def recalculate_mults(self):
    """Recalculate all points from scratch (called after ADIF import).
    Iterates contacts in chronological order."""
    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        my_grid = self.station.get("GridSquare", "")
        their_grid = contact.get("Exchange1", "")
        if their_grid and len(their_grid) >= 4:
            base = distance(my_grid, their_grid)
        else:
            base = 0
        band = contact.get("Band", "")
        mm_factor = 1
        for mm_band, factor in MM_FACTOR.items():
            if band == bandinMHz(mm_band):
                mm_factor = factor
                break
        contact["Points"] = int(base * mm_factor)
        self.database.change_contact(contact)


def edi(self):
    """Generate EDI log file (one file per band)."""
    value = self.contest_settings.get("StartDate", "")
    start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
    gen_edi(
        self,
        cabrillo_name,
        "IARU R1 VHF & Up Contest",
        start_date,
        start_date,
    )


def cabrillo(self, file_encoding):
    """Generate Cabrillo log file."""
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


def adif(self):
    """Generate ADIF log file."""
    value = self.contest_settings.get("StartDate", "")
    start_date = f"{value[0:4]}{value[5:7]}{value[8:10]}"
    gen_adif(
        self,
        cabrillo_name,
        "IARU R1 VHF & Up Contest",
        start_date,
        start_date,
    )


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
    """Show call history info for the callsign in the info line."""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('Exch1', '')}, {result.get('UserText', '...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """Check call history when callsign is entered."""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText', '')}")
        if self.other_1.text() == "":
            self.other_1.setText(f"{result.get('Exch1', '')}")
