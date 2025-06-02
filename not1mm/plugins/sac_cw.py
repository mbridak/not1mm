"""SAC CW plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import


import datetime
import logging

# import time
# from not1mm.lib.ham_utility import get_logged_band
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "#"

name = "SAC CW"
cabrillo_name = "SAC-CW"
mode = "CW"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 5, 6, 9, 11, 15]
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2

scandinavian_prefixes = [
    "JW",
    "JX",
    "LA",
    "LB",
    "LC",
    "LG",
    "LI",
    "LJ",
    "LN",
    "OF",
    "OG",
    "OH",
    "OI",
    "OFØ",
    "OGØ",
    "OHØ",
    "OJØ",
    "OX",
    "XP",
    "OW",
    "OY",
    "5P",
    "5Q",
    "OU",
    "OV",
    "OZ",
    "7S",
    "8S",
    "SA",
    "SB",
    "SC",
    "SD",
    "SE",
    "SF",
    "SG",
    "SH",
    "SI",
    "SJ",
    "SK",
    "SL",
    "SM",
    "TF",
]


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
    self.other_label.setText("SentNR")
    self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText("RcvNR")
    self.field4.setAccessibleName("Received Number")


def reset_label(self):  # pylint: disable=unused-argument
    """reset label after field cleared"""


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
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)


def points(self):
    """Calc point"""
    # 7.1 For Scandinavian stations:
    #   EUROPEAN stations, outside Scandinavia, are worth two (2) points for every complete QSO.
    #   NON-EUROPEAN stations are worth three (3) points for every complete QSO.
    # 7.2 For non-Scandinavian stations:
    #   EUROPEAN stations receive one (1) point for every complete Scandinavian QSO.
    #   NON-EUROPEAN stations receive one (1) point for every complete Scandinavian QSO on
    #       14, 21, and 28 MHz and three (3) points for every complete QSO on 3.5 and 7 MHz.

    if self.contact_is_dupe > 0:
        return 0

    myprimary_pfx = ""
    mycontinent = ""
    hisprimary_pfx = ""
    hiscontinent = ""

    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        item = result.get(next(iter(result)))
        myprimary_pfx = item.get("primary_pfx", "")
        mycontinent = item.get("continent", "")

    result = self.cty_lookup(self.contact.get("Call", ""))
    if result:
        item = result.get(next(iter(result)))
        hisprimary_pfx = item.get("primary_pfx", "")
        hiscontinent = item.get("continent", "")

    if (
        myprimary_pfx in scandinavian_prefixes
        and hisprimary_pfx not in scandinavian_prefixes
    ):
        if hiscontinent == "EU":
            return 2
        return 3
    if (
        myprimary_pfx not in scandinavian_prefixes
        and hisprimary_pfx in scandinavian_prefixes
    ):
        if mycontinent == "EU":
            return 1
        if self.contact.get("Band", 0) in ["3.5", "7"]:
            return 3
        if self.contact.get("Band", 0) in ["14", "21", "28"]:
            return 1

    # Something wrong
    return 0


def show_mults(self):
    """Return display string for mults"""
    myprimary_pfx = ""
    mult_count = 0

    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        myprimary_pfx = item.get("primary_pfx", "")

    if myprimary_pfx in scandinavian_prefixes:
        result = self.database.fetch_country_band_count()
        mult_count = result.get("cb_count", 0)
    else:
        query = f"SELECT count(DISTINCT(CountryPrefix || ':' || substr(WPXPrefix,3,1) || ':' || Band)) as mults from DXLOG where ContestNR = {self.pref.get('contest', '1')} AND CountryPrefix IN ('JW', 'JX', 'LA', 'LB', 'LC', 'LG', 'LI', 'LJ' , 'LN', 'OF', 'OG', 'OH', 'OI', 'OFØ', 'OGØ', 'OHØ', 'OJØ', 'OX', 'XP', 'OW', 'OY', '5P', '5Q', 'OU', 'OV', 'OZ', '7S', '8S', 'SA', 'SB', 'SC', 'SD', 'SE', 'SF', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'TF');"
        result = self.database.exec_sql(query)
        mult_count = result.get("mults", 0)
    return mult_count


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)
        mults = show_mults(self)
        return contest_points * mults
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "SAC-CW")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
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
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper()}_{cabrillo_name}_{date_time}.log"
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
                f"CALLSIGN: {self.station.get('Call','')}",
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
            ops = f"@{self.station.get('Call','')}"
            list_of_ops = self.database.get_ops()
            for op in list_of_ops:
                ops += f", {op.get('Operator', '')}"
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
                if themode == "LSB" or themode == "USB":
                    themode = "PH"
                frequency = str(int(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
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

    # print(f"checking esm {self.current_widget=} {with_enter=} {self.pref.get("run_state")=}")

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

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif self.other_2.text().isnumeric():
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

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

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif self.other_2.text().isnumeric():
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    self.process_function_key(button)


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["wpxprefix"] = show_mults(self)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)


# def add_test_data(self):
#     """"""
#     filename = "/home/mbridak/Nextcloud/dev/not1mm/research/sac/sac_log.txt"
#     try:
#         with open(filename, "rt", encoding="utf-8") as file_descriptor:
#             lines = file_descriptor.readlines()
#             for line in lines:
#                 field = line.split()
#                 print(f"{field[8]} {field[10]}")
#                 self.callsign.setText(str(field[8]))
#                 time.sleep(1.0)
#                 self.other_2.setText(str(field[10]))
#                 time.sleep(1.0)

#     except (FileNotFoundError, IndexError) as err:
#         print(f"{err=}")


# def set_self(the_outie):
#     """..."""
#     globals()["ALTEREGO"] = the_outie


# def ft8_handler(the_packet: dict):
#     """Process FT8 QSO packets

#     FlDigi
#     {
#             'FREQ': '7.029500',
#             'CALL': 'DL2DSL',
#             'MODE': 'RTTY',
#             'NAME': 'BOB',result = ALTEREGO.database.fetch_call_exists(the_packet.get("CALL", ""))
#         if result.get("call_count", ""):
#             ALTEREGO.contact["IsMultiplier1"] = 0
#         else:
#             ALTEREGO.contact["IsMultiplier1"] = 1
#             'QSO_DATE': '20240904',
#             'QSO_DATE_OFF': '20240904',
#             'TIME_OFF': '212825',
#             'TIME_ON': '212800',
#             'RST_RCVD': '599',
#             'RST_SENT': '599',
#             'BAND': '40M',
#             'COUNTRY': 'FED. REP. OF GERMANY',
#             'CQZ': '14',
#             'STX': '000',
#             'STX_STRING': '1D ORG',
#             'CLASS': '1D',
#             'ARRL_SECT': 'DX',
#             'TX_PWR': '0',
#             'OPERATOR': 'K6GTE',
#             'STATION_CALLSIGN': 'K6GTE',
#             'MY_GRIDSQUARE': 'DM13AT',
#             'MY_CITY': 'ANAHEIM, CA',
#             'MY_STATE': 'CA'
#         }

#     """
#     logger.debug(f"{the_packet=}")
#     if ALTEREGO is not None:
#         ALTEREGO.callsign.setText(the_packet.get("CALL"))
#         ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
#         ALTEREGO.contact["SNT"] = ALTEREGO.sent.text()
#         ALTEREGO.contact["RCV"] = ALTEREGO.receive.text()
#         ALTEREGO.contact["NR"] = the_packet.get("SRX_STRING", "001")
#         ALTEREGO.other_2.setText(the_packet.get("SRX_STRING", "001"))
#         ALTEREGO.other_1.setText(the_packet.get("STX_STRING", "001"))
#         ALTEREGO.contact["SentNr"] = the_packet.get("STX_STRING", "001")

#         ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
#         ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)

#         ALTEREGO.contact["QSXFreq"] = round(
#             float(the_packet.get("FREQ", "0.0")) * 1000, 2
#         )
#         ALTEREGO.contact["Band"] = get_logged_band(
#             str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
#         )
#         result = ALTEREGO.cty_lookup(the_packet.get("CALL"))
#         if result:
#             for a in result.items():
#                 entity = a[1].get("entity", "")
#                 cq = a[1].get("cq", "")
#                 itu = a[1].get("itu", "")
#                 continent = a[1].get("continent")
#                 primary_pfx = a[1].get("primary_pfx", "")
#                 ALTEREGO.contact["CountryPrefix"] = primary_pfx
#                 ALTEREGO.contact["Continent"] = continent
#         ALTEREGO.radio_state["vfoa"] = int(
#             float(the_packet.get("FREQ", "0.0")) * 1000000
#         )
#         logger.debug(f"{ALTEREGO.contact=}")
#         ALTEREGO.save_contact()
