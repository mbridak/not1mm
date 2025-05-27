"""
His Maj. King of Spain Contest, SSB
Status:	            Active
Geographic Focus:	Worldwide
Participation:	    Worldwide
Awards:	            Worldwide
Mode:	            SSB
Bands:	            160, 80, 40, 20, 15, 10m
Classes:	        Single Op All Band (QRP/Low/High)
                    Single Op All Band Youth
                    Single Op Single Band
                    Multi-Op (Low/High)
Max power:	        HP: >100 watts
                    LP: 100 watts
                    QRP: 5 watts
Exchange:	        EA: RST + province
                    non-EA: RST + Serial No.
Work stations:	    Once per band
QSO Points:	        (see rules)
Multipliers:	    Each EA province once per band
                    Each EADX100 entity once per band
                    Each special (EA0) station once per band
Score Calculation:	Total score = total QSO points x total mults
E-mail logs to:	    (none)
Upload log at:	    https://concursos.ure.es/en/logs/
Mail logs to:	    (none)
Find rules at:	    https://concursos.ure.es/en/s-m-el-rey-de-espana-ssb/bases/
Cabrillo name:	    EA-MAJESTAD-SSB
"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member

# EA1: AV, BU, C, LE, LO, LU, O, OU, P, PO, S, SA, SG, SO, VA, ZA
# EA2: BI, HU, NA, SS, TE, VI, Z
# EA3: B, GI, L, T
# EA4: BA, CC, CR, CU, GU, M, TO
# EA5: A, AB, CS, MU, V
# EA6: IB
# EA7: AL, CA, CO, GR, H, J, MA, SE
# EA8: GC, TF
# EA9: CE, ML


import datetime
import logging

from pathlib import Path
from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import get_logged_band
from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Province or #"

name = "His Maj. King of Spain Contest, SSB"
mode = "SSB"  # CW SSB BOTH RTTY
cabrillo_name = "EA-MAJESTAD-SSB"

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


def init_contest(self) -> None:
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self) -> None:
    """
    Setup the user interface.
    Unhides the input fields and sets the lebels.
    """
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.other_label.setText("SentNR")
    self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText("Prov or SN")
    self.field4.setAccessibleName("Province or Serial Number")


def reset_label(self) -> None:
    """
    Reset label after field cleared.
    Not needed for this contest.
    """


def set_tab_next(self) -> None:
    """
    Set TAB Advances.
    Defines which which of the fields are next to get focus when the TAB key is pressed.
    """
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self) -> None:
    """
    Set TAB Advances.
    Defines which which of the fields are next to get focus when the Shift-TAB key is pressed.
    """
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def validate(self) -> bool:
    """Not Used"""
    return True


def set_contact_vars(self) -> None:
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.other_1.text()


def predupe(self) -> None:
    """called after callsign entered. Not needed here."""


def prefill(self) -> None:
    """
    Fill the SentNR field with either the next serial number or the province.
    """
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"

    exchange = self.contest_settings.get("SentExchange", "").replace("#", serial_nr)
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exchange)


def points(self) -> int:
    """
    Calculate the points for this contact.
    """
    # EA: 2 points per QSO with EA
    # EA: 1 point per QSO with non-EA
    # non-EA: 3 points per QSO with EA
    # non-EA: 1 point per QSO with non-EA

    if self.contact_is_dupe > 0:
        return 0

    ea_prefixes = ["EA", "EA1", "EA2", "EA3", "EA4", "EA5", "EA6", "EA7", "EA8", "EA9"]

    me = None
    him = None

    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        me = item.get("primary_pfx", "")

    result = self.cty_lookup(self.contact.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        him = item.get("primary_pfx", "")

    if me is not None and him is not None:
        if me in ea_prefixes and him in ea_prefixes:
            return 2
        elif me in ea_prefixes and him not in ea_prefixes:
            return 1
        elif me not in ea_prefixes and him in ea_prefixes:
            return 3
        else:
            return 1

    return 1


def show_mults(self, rtc=None) -> int:
    """Return display string for mults"""

    ea_provinces = 0
    # dx = 0
    ef0f = 0
    eadx100 = 0

    # Each EADX100 entity once per band
    sql = (
        "select count(DISTINCT(CountryPrefix || ':' || Band)) as mult_count "
        f"from dxlog where ContestNR = {self.database.current_contest};"
    )
    result = self.database.exec_sql(sql)
    if result:
        eadx100 = result.get("mult_count", 0)

    # Each EA province once per band
    sql = (
        "select count(DISTINCT(NR || ':' || Band)) as mult_count "
        f"from dxlog where ContestNR = {self.database.current_contest} and typeof(NR) = 'text';"
    )
    result = self.database.exec_sql(sql)
    if result:
        ea_provinces = result.get("mult_count", 0)

    # Each QSO with EF0F/8 once per band
    sql = (
        "select count(DISTINCT(Band)) as mult_count "
        f"from dxlog where Call = 'EF0F/8' and ContestNR = {self.database.current_contest};"
    )
    result = self.database.exec_sql(sql)
    if result:
        ef0f = result.get("mult_count", 0)

    if rtc is not None:
        return 0, 0

    return ea_provinces + ef0f + eadx100


def show_qso(self) -> int:
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self) -> int:
    """Return calculated score"""
    _points = get_points(self)
    _mults = show_mults(self)

    return _points * _mults


def adif(self) -> None:
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, contest_id=cabrillo_name)


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


def recalculate_mults(self) -> None:
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
                    if button == self.esm_dict["HISCALL"]:
                        self.process_function_key(button, rttysendrx=False)
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
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, {result.get('Exch1', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Exch1', '')}")


def get_mults(self):
    """"""
    mults = {}
    mults["country"], mults["state"] = show_mults(self, rtc=True)
    return mults


def just_points(self):
    """"""
    return get_points(self)


def set_self(the_outie):
    """..."""
    globals()["ALTEREGO"] = the_outie


def ft8_handler(the_packet: dict):
    print(f"{the_packet=}")
    """Process FT8 QSO packets
    # FT8
    # {
    #     'CALL': 'KE0OG',
    #     'GRIDSQUARE': 'DM10AT',
    #     'MODE': 'FT8',
    #     'RST_SENT': '',
    #     'RST_RCVD': '',
    #     'QSO_DATE': '20210329',
    #     'TIME_ON': '183213',
    #     'QSO_DATE_OFF': '20210329',
    #     'TIME_OFF': '183213',
    #     'BAND': '20M',
    #     'FREQ': '14.074754',
    #     'STATION_CALLSIGN': 'K6GTE',
    #     'MY_GRIDSQUARE': 'DM13AT',
    #     'CONTEST_ID': 'ARRL-FIELD-DAY',
    #     'SRX_STRING': '1D UT',
    #     'CLASS': '1D',
    #     'ARRL_SECT': 'UT'
    # }
    # FlDigi
    # {
    #     'CALL': 'K5TUS', 
    #     'MODE': 'RTTY', 
    #     'FREQ': '14.068415', 
    #     'BAND': '20M', 
    #     'QSO_DATE': '20250103', 
    #     'TIME_ON': '2359', 
    #     'QSO_DATE_OFF': '20250103', 
    #     'TIME_OFF': '2359', 
    #     'NAME': '', 
    #     'QTH': '', 
    #     'STATE': 'ORG', 
    #     'VE_PROV': '', 
    #     'COUNTRY': 'USA', 
    #     'RST_SENT': '599', 
    #     'RST_RCVD': '599', 
    #     'TX_PWR': '0', 
    #     'CNTY': '', 
    #     'DXCC': '', 
    #     'CQZ': '5', 
    #     'IOTA': '', 
    #     'CONT': '', 
    #     'ITUZ': '', 
    #     'GRIDSQUARE': '', 
    #     'QSLRDATE': '', 
    #     'QSLSDATE': '', 
    #     'EQSLRDATE': '', 
    #     'EQSLSDATE': '', 
    #     'LOTWRDATE': '', 
    #     'LOTWSDATE': '', 
    #     'QSL_VIA': '', 
    #     'NOTES': '', 
    #     'SRX': '', 
    #     'STX': '000', 
    #     'SRX_STRING': '', 
    #     'STX_STRING': 'CA', 


    #     'SRX': '666', 
    #     'STX': '000', 
    #     'SRX_STRING': '', 
    #     'STX_STRING': 'CA',

    #     'SRX': '004', 'STX': '000', 'SRX_STRING': '', 'STX_STRING': '#',

    #     'CLASS': '', 
    #     'ARRL_SECT': '', 
    #     'OPERATOR': 'K6GTE', 
    #     'STATION_CALLSIGN': 'K6GTE', 
    #     'MY_GRIDSQUARE': 'DM13AT', 
    #     'MY_CITY': 'ANAHEIM, CA', 
    #     'CHECK': '', 
    #     'AGE': '', 
    #     'TEN_TEN': '', 
    #     'CWSS_PREC': '', 
    #     'CWSS_SECTION': '', 
    #     'CWSS_SERNO': '', 
    #     'CWSS_CHK': ''
    # }

    # """

    # logger.debug(f"{the_packet=}")
    # if ALTEREGO is not None:
    #     ALTEREGO.callsign.setText(the_packet.get("CALL"))
    #     ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
    #     ALTEREGO.contact["SNT"] = the_packet.get("RST_SENT", "599")
    #     ALTEREGO.contact["RCV"] = the_packet.get("RST_RCVD", "599")

    #     sent_string = the_packet.get("STX_STRING", "")
    #     if sent_string != "":
    #         ALTEREGO.contact["SentNr"] = sent_string
    #         ALTEREGO.other_1.setText(str(sent_string))
    #     else:
    #         ALTEREGO.contact["SentNr"] = the_packet.get("STX", "000")
    #         ALTEREGO.other_1.setText(str(the_packet.get("STX", "000")))

    #     rx_string = the_packet.get("SRX_STRING", "")
    #     if rx_string != "":
    #         ALTEREGO.contact["NR"] = rx_string
    #         ALTEREGO.other_2.setText(str(rx_string))
    #     else:
    #         ALTEREGO.contact["NR"] = the_packet.get("SRX", "000")
    #         ALTEREGO.other_2.setText(str(the_packet.get("SRX", "000")))

    #     ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
    #     ALTEREGO.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
    #     ALTEREGO.contact["QSXFreq"] = round(
    #         float(the_packet.get("FREQ", "0.0")) * 1000, 2
    #     )
    #     ALTEREGO.contact["Band"] = get_logged_band(
    #         str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
    #     )
    #     logger.debug(f"{ALTEREGO.contact=}")

    #     ALTEREGO.save_contact()
