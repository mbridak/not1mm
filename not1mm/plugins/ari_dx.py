"""ARI International DX Contest"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import, line-too-long
# pyright: ignore[reportUndefinedVariable]
# pylance: disable=reportUndefinedVariable
# ruff: noqa: F821
# ruff: noqa: F401

# Status:	            Active
# Geographic Focus:     Worldwide
# Participation:        Worldwide
# Awards:	            Worldwide
# Mode:	                Phone, CW, RTTY
# Bands:	            80, 40, 20, 15, 10m
# Classes:	            Single Op (CW/SSB/RTTY/Mixed)(Low/High)
#                       Single Op Overlays (Italian only): (Rookie/Youth)
#                       Multi-Single
#                       Multi-Multi
#                       SWL
# Max power:            HP: >100 watts
#                       LP: 100 watts
# Exchange:             I: RS(T) + 2-letter province
#                       non-I: RS(T) + Serial No.
# Work stations:        Once per mode per band
# QSO Points:           0 points per QSO with same country
#                       1 point per QSO with different country same continent
#                       3 points per QSO with different continent
#                       10 points per QSO with I/IS0/IT9 stations
# Multipliers:          Each Italian province once per band
#                       Each DXCC country once per band
# Score Calculation:    Total score = total QSO points x total mults
# E-mail logs to:       (none)
# Upload log at:        https://www.ari.it/contest-hf/ari-international/log-upload.html
# Mail logs to:         (none)
# Find rules at:        https://www.ari.it/
# Cabrillo name:	    ARI-DX


import datetime
import logging
import platform

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import get_logged_band
from not1mm.lib.plugin_common import gen_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Prov or '#'"

name = "ARI International DX"
cabrillo_name = "ARI-DX"
mode = "BOTH"  # CW SSB BOTH RTTY

columns = [
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

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 3


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
    self.exch_label.setText("Prov or SN")
    self.field4.setAccessibleName("Province or Serial Number")


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
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.other_1.text()


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill sentnr"""
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"

    exchange = self.contest_settings.get("SentExchange", "").replace("#", serial_nr)
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exchange)


def points(self) -> int:
    """Calc point"""

    # QSO Points:           0 points per QSO with same country
    #                       1 point per QSO with different country same continent
    #                       3 points per QSO with different continent
    #                       10 points per QSO with I/IS0/IT9 stations

    if self.contact_is_dupe > 0:
        return 0

    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        mycountry = item.get("primary_pfx", "")
        # myentity = item.get("entity", "")
        mycontinent = item.get("continent", "")

    result = self.cty_lookup(self.contact.get("Call", ""))
    print(f"{result=}")
    if result is not None:
        item = result.get(next(iter(result)))
        hiscountry = item.get("primary_pfx", "")
        # hisentity = item.get("entity", "")
        hiscontinent = item.get("continent", "")

    _points = 0

    if mycountry == hiscountry:
        _points = 0
    if mycountry != hiscountry and mycontinent == hiscontinent:
        _points = 1
    if mycontinent != hiscontinent:
        _points = 3
    if hiscountry in ("I", "IS0", "IT9"):
        _points = 10

    return _points


def show_mults(self):
    """Return display string for mults"""

    # Multipliers:          Each Italian province once per band
    #                       Each DXCC country once per band

    _country = 0
    _province = 0

    sql = (
        "select count(DISTINCT(NR || ':' || Band)) as mult_count from dxlog "
        f"where ContestNR = {self.database.current_contest} and typeof(NR) = 'text';"
    )
    result = self.database.exec_sql(sql)
    if result:
        _province = result.get("mult_count", 0)

    sql = (
        "select count(DISTINCT(CountryPrefix || ':' || Band)) as cb_count from dxlog "
        f"where ContestNR = {self.database.current_contest} and CountryPrefix NOT in ('I', 'IS');"
    )
    result2 = self.database.exec_sql(sql)
    if result2:
        _country = int(result2.get("cb_count", 0))

    return _country + _province


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
        mults = int(show_mults(self))
        return contest_points * mults
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, cabrillo_name)


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
    # https://www.cw160.com/cabrillo.htm
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
                if themode == "RTTY":
                    themode = "RY"
                frequency = str(int(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '')).upper().ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '')).upper().ljust(6)}",
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


def trigger_update(self):
    """Triggers the log window to update."""
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if self.log_window:
        self.log_window.msg_from_main(cmd)


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
            if self.other_2.text() == "":
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
            if self.other_2.text() == "":
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
        self.history_info.setText(f"{result.get('Call', '')}, {result.get('Sect', '')}")
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Sect', '')}")


def set_self(the_outie):
    """..."""
    globals()["ALTEREGO"] = the_outie


def ft8_handler(the_packet: dict):
    print(f"{the_packet=}")
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
        'CALL': 'K5TUS', 
        'MODE': 'RTTY', 
        'FREQ': '14.068415', 
        'BAND': '20M', 
        'QSO_DATE': '20250103', 
        'TIME_ON': '2359', 
        'QSO_DATE_OFF': '20250103', 
        'TIME_OFF': '2359', 
        'NAME': '', 
        'QTH': '', 
        'STATE': 'ORG', 
        'VE_PROV': '', 
        'COUNTRY': 'USA', 
        'RST_SENT': '599', 
        'RST_RCVD': '599', 
        'TX_PWR': '0', 
        'CNTY': '', 
        'DXCC': '', 
        'CQZ': '5', 
        'IOTA': '', 
        'CONT': '', 
        'ITUZ': '', 
        'GRIDSQUARE': '', 
        'QSLRDATE': '', 
        'QSLSDATE': '', 
        'EQSLRDATE': '', 
        'EQSLSDATE': '', 
        'LOTWRDATE': '', 
        'LOTWSDATE': '', 
        'QSL_VIA': '', 
        'NOTES': '', 
        'SRX': '', 
        'STX': '000', 
        'SRX_STRING': '', 
        'STX_STRING': 'CA', 


        'SRX': '666', 
        'STX': '000', 
        'SRX_STRING': '', 
        'STX_STRING': 'CA',

        'SRX': '004', 'STX': '000', 'SRX_STRING': '', 'STX_STRING': '#',

        'CLASS': '', 
        'ARRL_SECT': '', 
        'OPERATOR': 'K6GTE', 
        'STATION_CALLSIGN': 'K6GTE', 
        'MY_GRIDSQUARE': 'DM13AT', 
        'MY_CITY': 'ANAHEIM, CA', 
        'CHECK': '', 
        'AGE': '', 
        'TEN_TEN': '', 
        'CWSS_PREC': '', 
        'CWSS_SECTION': '', 
        'CWSS_SERNO': '', 
        'CWSS_CHK': ''
    }

    """
    logger.debug(f"{the_packet=}")
    if ALTEREGO is not None:  # type: ignore
        ALTEREGO.callsign.setText(the_packet.get("CALL"))  # type: ignore
        ALTEREGO.contact["Call"] = the_packet.get("CALL", "")  # type: ignore
        ALTEREGO.contact["SNT"] = the_packet.get("RST_SENT", "599")  # type: ignore
        ALTEREGO.contact["RCV"] = the_packet.get("RST_RCVD", "599")  # type: ignore

        sent_string = the_packet.get("STX_STRING", "")
        if sent_string != "":
            ALTEREGO.contact["SentNr"] = sent_string  # type: ignore
            ALTEREGO.other_1.setText(str(sent_string))  # type: ignore
        else:
            ALTEREGO.contact["SentNr"] = the_packet.get("STX", "000")  # type: ignore
            ALTEREGO.other_1.setText(str(the_packet.get("STX", "000")))  # type: ignore

        rx_string = the_packet.get("STATE", "")
        if rx_string != "":
            ALTEREGO.contact["NR"] = rx_string  # type: ignore
            ALTEREGO.other_2.setText(str(rx_string))  # type: ignore
        else:
            ALTEREGO.contact["NR"] = the_packet.get("SRX", "000")  # type: ignore
            ALTEREGO.other_2.setText(str(the_packet.get("SRX", "000")))  # type: ignore

        ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")  # type: ignore
        ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)  # type: ignore
        ALTEREGO.contact["QSXFreq"] = round(  # type: ignore
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        ALTEREGO.contact["Band"] = get_logged_band(  # type: ignore
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        logger.debug(f"{ALTEREGO.contact=}")  # type: ignore

        ALTEREGO.save_contact()  # type: ignore
