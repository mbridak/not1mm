"""CQ World-Wide VHF Contest plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

#   CQ World-Wide VHF Contest
#   Status: Active
#   Geographic Focus: Worldwide
#   Participation: Worldwide
#   Mode: SSB/CW/FM weekend, Digital (FT4/FT8/MSK144/Q65 etc.) weekend
#   Bands: 50 MHz (6m) and 144 MHz (2m) only
#   Classes: SINGLE-OP (HIGH/LOW/QRP), HILLTOPPER, ROVER, MULTI-OP, CHECKLOG
#   Max power: 1500 watts (High), 100 watts (Low), 10 watts (QRP)
#   Exchange: 4-character Maidenhead grid locator (no signal reports)
#   Work stations: Once per band
#   QSO Points: 1 point per 50 MHz QSO, 2 points per 144 MHz QSO
#   Multipliers: Grid locators once per band
#     Rovers: contacts/mults count as new from each new grid visited
#   Score Calculation: Total score = total QSO points x total mults
#   Upload log at: https://cqww-vhf.com/logcheck/
#   Find rules at: https://cqww-vhf.com/rules/
#   Cabrillo name: CQ-VHF-SSBCW / CQ-VHF-DIGI

import datetime
import logging

from pathlib import Path
from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import get_logged_band
from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

ALTEREGO = None
EXCHANGE_HINT = "4-character grid square"
SOAPBOX_HINT = "CQ WW VHF - Exchange is your 4 digit gridsquare"

name = "CQ WW VHF"
mode = "BOTH"  # CW SSB BOTH RTTY
cabrillo_name = "CQ-VHF-SSBCW"

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "SentNr",
    "RcvNr",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.hide()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.other_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "Sent Grid")
    )
    self.field3.setAccessibleName("Sent Grid")
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "Grid"))
    self.field4.setAccessibleName("Gridsquare")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.other_2: self.other_1,
        self.other_1: self.callsign,
    }


def normalize_grid(text: str) -> str:
    """Extract a valid 4-character Maidenhead grid locator from text.

    A valid locator is two letters, two digits, e.g. EM15.
    Longer locators are truncated to their 4-character field designator.
    """

    candidate = text.upper().strip().split()[0] if text.strip() else ""
    if len(candidate) >= 4:
        candidate = candidate[:4]
    if len(candidate) == 4 and candidate[:2].isalpha() and candidate[2:].isdigit():
        return candidate
    return ""


def validate_exchange(text: str) -> bool:
    """Return True if the text contains a valid 4-character grid."""

    return normalize_grid(text) != ""


def points_for_band(band: str) -> int:
    """Return QSO points for a band. 6m = 1 point, 2m = 2 points."""

    if band in ("50", "6"):
        return 1
    if band in ("144", "2"):
        return 2
    return 0


def cabrillo_contest_name(contest_settings: dict) -> str:
    """Return the correct Cabrillo contest name based on the mode category.

    The digital weekend uses CQ-VHF-DIGI, everything else CQ-VHF-SSBCW.
    """

    mode_category = contest_settings.get("ModeCategory", "")
    return "CQ-VHF-DIGI" if mode_category == "DIGITAL" else "CQ-VHF-SSBCW"


def cabrillo_mode(mode_category: str) -> str:
    """Map not1mm mode category to a valid Cabrillo CATEGORY-MODE value.

    Valid entries for the CQ WW VHF robot are: SSB CW DG FM MIXED.
    """

    mapping = {
        "CW": "CW",
        "SSB": "SSB",
        "FM": "FM",
        "DIGITAL": "DG",
        "SSB+CW": "MIXED",
        "SSB+CW+DIGITAL": "MIXED",
        "RTTY": "DG",
        "PSK": "DG",
    }
    return mapping.get(mode_category.upper(), mode_category)


def validate(self):
    """Validate the exchange entry."""
    return validate_exchange(self.other_2.text())


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = ""
    self.contact["RCV"] = ""
    self.contact["NR"] = normalize_grid(self.other_2.text())
    self.contact["SentNr"] = normalize_grid(self.other_1.text())


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill sentnr"""
    exchange = self.contest_settings.get("SentExchange", "").upper()
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exchange)


def points(self):
    """Calc point"""

    # QSO Points: 1 point per 50 MHz QSO, 2 points per 144 MHz QSO

    if self.contact_is_dupe > 0:
        return 0

    _band = self.contact.get("Band", "")
    return points_for_band(_band)


def show_mults(self):
    """Return display string for mults"""
    # Multipliers: Grid squares once per band.
    # Rovers count grids anew from each location visited.

    dx = 0

    sql = (
        "select count(DISTINCT(NR || ':' || Band || ':' || RoverLocation)) "
        "as mult_count "
        f"from dxlog where ContestNR = {self.database.current_contest} "
        "and typeof(NR) = 'text';"
    )
    result = self.database.exec_sql(sql)

    if result:
        dx = result.get("mult_count", 0)

    return dx


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    # Total score = total QSO points x total mults
    _points = get_points(self)
    _mults = show_mults(self)
    return _points * _mults


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name)


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
    # https://cqww-vhf.com/cabrillo.htm
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper().replace('/','-')}_{cabrillo_name}_{date_time}.log"
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
                f"CONTEST: {cabrillo_contest_name(self.contest_settings)}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            if self.station.get("Club", ""):
                output_cabrillo_line(
                    f"CLUB: {self.station.get('Club', '')}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"CALLSIGN: {self.station.get('Call','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            location = self.station.get("ARRLSection", "")
            if not location:
                location = "DX"
            output_cabrillo_line(
                f"LOCATION: {location}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-OPERATOR: {self.contest_settings.get('OperatorCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-ASSISTED: {self.contest_settings.get('AssistedCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-BAND: {self.contest_settings.get('BandCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            mode = cabrillo_mode(self.contest_settings.get("ModeCategory", ""))
            output_cabrillo_line(
                f"CATEGORY-MODE: {mode}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-TRANSMITTER: {self.contest_settings.get('TransmitterCategory','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            if self.contest_settings.get("OverlayCategory", "") != "N/A":
                output_cabrillo_line(
                    f"CATEGORY-OVERLAY: {self.contest_settings.get('OverlayCategory','')}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line(
                f"GRID-LOCATOR: {self.station.get('GridSquare','')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"CATEGORY-POWER: {self.contest_settings.get('PowerCategory','')}",
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
                ops += f"{op.get('Operator', '')} "
            if self.station.get("Call", "") not in ops:
                ops += f"@{self.station.get('Call','')}"
            else:
                ops = ops.rstrip(" ")
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
                if themode in ("LSB", "USB", "AM"):
                    themode = "PH"
                freq = contact.get("Freq", "0") / 1000

                frequency = str(round(freq)).rjust(4)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('NR', '')).ljust(6)}",
                    "\r\n",
                    file_descriptor,
                    file_encoding,
                )
            output_cabrillo_line("END-OF-LOG:", "\r\n", file_descriptor, file_encoding)
        self.show_message_box(f"Cabrillo saved to: {filename}")
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""


def set_self(the_outie):
    """..."""
    globals()["ALTEREGO"] = the_outie


def ft8_handler(the_packet: dict):
    """Process FT8 QSO packets
    FT8
    {
        'CALL': 'KE0OG',
        'GRIDSQUARE': 'DM10AT',
        'MODE': 'FT8',
        'RST_SENT': '',
        'RST_RCVD': '',
        'QSO_DATE': '20210329',
        'TIME_ON': '183213',
        'QSO_DATE_OFF': '20210329',
        'TIME_OFF': '183213',
        'BAND': '20M',
        'FREQ': '14.074754',
        'STATION_CALLSIGN': 'K6GTE',
        'MY_GRIDSQUARE': 'DM13AT',
        'CONTEST_ID': 'CQ-VHF',
        'SRX_STRING': 'EM12',
        ...
    }
    """
    if ALTEREGO is not None:
        ALTEREGO.callsign.setText(the_packet.get("CALL"))
        ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
        my_grid = the_packet.get("MY_GRIDSQUARE", "")
        if my_grid:
            my_grid = normalize_grid(my_grid)
        their_grid = the_packet.get("GRIDSQUARE", "")
        if their_grid:
            their_grid = normalize_grid(their_grid)
        ALTEREGO.contact["NR"] = their_grid
        ALTEREGO.contact["SentNr"] = my_grid
        if the_packet.get("SUBMODE"):
            ALTEREGO.contact["Mode"] = the_packet.get("SUBMODE", "ERR")
        else:
            ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
        ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        ALTEREGO.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        ALTEREGO.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        ALTEREGO.contact["SNT"] = ""
        ALTEREGO.contact["RCV"] = ""
        ALTEREGO.other_1.setText(my_grid)
        ALTEREGO.other_2.setText(their_grid)
        ALTEREGO.save_contact()


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
        self.esm_dict["CQ"],
        self.esm_dict["EXCH"],
        self.esm_dict["QRZ"],
        self.esm_dict["AGN"],
        self.esm_dict["HISCALL"],
        self.esm_dict["MYCALL"],
        self.esm_dict["QSOB4"],
    ]:
        if a_button is not None:
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

        elif self.current_widget in ["other_2"]:
            if not validate_exchange(self.other_2.text()):
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

        elif self.current_widget in ["other_2"]:
            if not validate_exchange(self.other_2.text()):
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
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('Loc1', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Loc1', '')}")


def get_mults(self):
    """"""

    mults = {}
    mults["gridsquare"] = show_mults(self)
    return mults


def just_points(self):
    """"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        return int(score)
    return 0
