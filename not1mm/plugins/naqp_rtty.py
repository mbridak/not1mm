"""NAQP RTTY plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

# North American QSO Party, RTTY
#  	Status:	Active
#  	Geographic Focus:	North America
#  	Participation:	Worldwide
#  	Awards:	North America
#  	Mode:	RTTY
#  	Bands:	160, 80, 40, 20, 15, 10m
#  	Classes:	Single Op (QRP/Low)
# Single Op Assisted (QRP/Low)
# Single Op Overlay: Youth
# Multi-Two (Low)
# Max operating hours:  Single Op:  10 hours
#                       Multi-Two:  12 hours
# Max power:	LP: 100 watts
# QRP:          5 watts
# Exchange:	    NA: Name + (state/DC/province/country)
#               non-NA: Name
#  	Work stations:	Once per band
#  	QSO Points:	    NA station: 1 point per QSO
#                   non-NA station: 1 point per QSO with an NA station
#  	Multipliers:	Each US state and DC (including KH6/KL7) once per band
#                   Each VE province/territory once per band
#                   Each North American country (except W/VE) once per band
#  	Score Calculation:	Total score = total QSO points x total mults
#  	E-mail logs to:	(none)
#  	Upload log at:	http://www.ncjweb.com/naqplogsubmit/
#  	Mail logs to:	(none)
#  	Find rules at:	https://www.ncjweb.com/NAQP-Rules.pdf
#  	Cabrillo name:	NAQP-RTTY

import datetime
import logging
import platform

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import get_logged_band
from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Name or Name + SPC"

ALTEREGO = None

name = "NAQP RTTY"
cabrillo_name = "NAQP-RTTY"
mode = "RTTY"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 10, 11, 14, 15]
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Name",
    "Sect",
    "M1",
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
    self.next_field = self.other_1


def interface(self):
    """Setup user interface"""
    self.field1.hide()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.sent.setAccessibleName("RST Sent")
    self.other_label.setText("Name")
    self.other_1.setAccessibleName("Name")
    self.exch_label.setText("State")
    self.other_2.setAccessibleName("State")


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
        self.other_1: self.callsign,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["Name"] = self.other_1.text().upper()
    self.contact["Sect"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.contest_settings.get("SentExchange", 0)

    if self.contact.get("Sect", ""):
        result = self.database.fetch_sect_band_exists(
            self.contact.get("Sect", ""), self.contact.get("Band", "")
        )
        if result.get("sect_count", ""):
            self.contact["IsMultiplier1"] = 0
        else:
            self.contact["IsMultiplier1"] = 1


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill sentnr"""


def points(self):
    """Calc point"""
    if self.contact_is_dupe > 0:
        return 0
    mycontinent = ""
    hiscontinent = ""
    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        mycontinent = item.get("continent", "")
    result = self.cty_lookup(self.contact.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        hiscontinent = item.get("continent", "")
    if mycontinent == "NA" or hiscontinent == "NA":
        return 1
    return 0


def show_mults(self):
    """Return display string for mults"""
    result = self.database.fetch_section_band_count_nodx()
    if result:
        return int(result.get("sb_count", 0))
    return 0


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
    gen_adif(self, cabrillo_name, "NAQP-RTTY")


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
                if themode == "LSB" or themode == "USB":
                    themode = "PH"
                if themode.strip() in (
                    "RTTY",
                    "RTTY-R",
                    "LSB-D",
                    "USB-D",
                    "AM-D",
                    "FM-D",
                    "DIGI-U",
                    "DIGI-L",
                    "RTTYR",
                    "PKTLSB",
                    "PKTUSB",
                ):
                    themode = "RY"
                frequency = str(int(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SentNr', '')).upper()} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('Name', '')).ljust(11)} "
                    f"{str(contact.get('Sect', '')).ljust(5)}",
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

    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        time_stamp = contact.get("TS", "")
        sect = contact.get("Sect", "")
        band = contact.get("Band", "")
        query = (
            f"select count(*) as sect_count from dxlog where  TS < '{time_stamp}' "
            f"and Sect = '{sect}' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        count = result.get("sect_count", 1)
        if count == 0 and contact.get("Points", 0) == 1 and sect != "DX":
            contact["IsMultiplier1"] = 1
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)
        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if self.log_window:
            self.log_window.msg_from_main(cmd)


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
        'CONTEST_ID': 'ARRL-FIELD-DAY',
        'SRX_STRING': '1D UT',
        'CLASS': '1D',
        'ARRL_SECT': 'UT'
    }
    FlDigi
    {
            'FREQ': '7.029500',
            'CALL': 'DL2DSL',
            'MODE': 'RTTY',
            'NAME': 'BOB',
            'QSO_DATE': '20240904',
            'QSO_DATE_OFF': '20240904',
            'TIME_OFF': '212825',
            'TIME_ON': '212800',
            'RST_RCVD': '599',
            'RST_SENT': '599',
            'BAND': '40M',
            'COUNTRY': 'FED. REP. OF GERMANY',
            'CQZ': '14',
            'STX': '000',
            'STX_STRING': '1D ORG',
            'CLASS': '1D',
            'ARRL_SECT': 'DX',
            'TX_PWR': '0',
            'OPERATOR': 'K6GTE',
            'STATION_CALLSIGN': 'K6GTE',
            'MY_GRIDSQUARE': 'DM13AT',
            'MY_CITY': 'ANAHEIM, CA',
            'MY_STATE': 'CA'
        }

    """
    logger.debug(f"{the_packet=}")
    print(f"{the_packet=}")
    # the_packet=
    # {
    # 'FREQ': '14.028415', 'CALL': 'K5TUY', 'MODE': 'RTTY', 'NAME': 'RUSS', 'QSO_DATE': '20241015',
    # 'QSO_DATE_OFF': '20241015', 'TIME_OFF': '131334', 'TIME_ON': '130300', 'RST_RCVD': '599', 'RST_SENT': '599',
    # 'BAND': '20M', 'COUNTRY': 'USA', 'CQZ': '5', 'STX': '000', 'SRX_STRING': 'MO', 'STX_STRING': 'DM13',
    # 'TX_PWR': '0', 'OPERATOR': 'K6GTE', 'STATION_CALLSIGN': 'K6GTE', 'MY_GRIDSQUARE': 'DM13AT',
    # 'MY_CITY': 'ANAHEIM, CA', 'MY_STATE': 'CA'
    # }
    if ALTEREGO is not None:
        ALTEREGO.callsign.setText(the_packet.get("CALL"))
        ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
        ALTEREGO.contact["SNT"] = ALTEREGO.sent.text()
        ALTEREGO.contact["RCV"] = ALTEREGO.receive.text()
        ALTEREGO.other_1.setText(str(the_packet.get("NAME", "")))
        ALTEREGO.other_2.setText(f'{the_packet.get("SRX_STRING", "")}'.strip())
        ALTEREGO.contact["ZN"] = the_packet.get("CQZ", "")
        ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
        ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        ALTEREGO.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        ALTEREGO.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        logger.debug(f"{ALTEREGO.contact=}")

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

        elif self.current_widget == "other_1" or self.current_widget == "other_2":
            continent = self.contact.get("Continent")
            if self.other_1.text() == "" or (
                self.other_2.text() == "" and continent == "NA"
            ):
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif (
                self.other_1.text().isalpha()
                and self.other_2.text().isalpha()
                and continent == "NA"
            ):
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")
            elif self.other_1.text().isalpha() and continent != "NA":
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

        if with_enter is True and bool(len(buttons_to_send)):
            sendstring = ""
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    sendstring = f"{sendstring}{self.process_macro(button.toolTip())} "
            self.fldigi_util.send_string(sendstring)
    else:
        if self.current_widget == "callsign":
            if len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["MYCALL"])
                buttons_to_send.append(self.esm_dict["MYCALL"])

        elif self.current_widget == "other_1" or self.current_widget == "other_2":
            continent = self.contact.get("Continent")
            if self.other_1.text() == "" or (
                self.other_2.text() == "" and continent == "NA"
            ):
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            elif (
                self.other_1.text().isalpha()
                and self.other_2.text().isalpha()
                and continent == "NA"
            ):
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")
            elif self.other_1.text().isalpha() and continent != "NA":
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

        if with_enter is True and bool(len(buttons_to_send)):
            sendstring = ""
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        continue
                    sendstring = f"{sendstring}{self.process_macro(button.toolTip())} "
            self.fldigi_util.send_string(sendstring)


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('State', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_1.text() == "":
            self.other_1.setText(f"{result.get('Name', '')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('State', '')}")


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["state"] = show_mults(self)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
