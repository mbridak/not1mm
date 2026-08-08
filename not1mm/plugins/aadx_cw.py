"""ALL ASIA CW plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import

# ALL ASIA DX Contest, CW
#  	Status:	Active
#  	Geographic Focus:	Worldwide
#  	Participation:	Worldwide
#  	Awards:	Worldwide
#  	Mode:	CW
#  	Bands:	160, 80, 40, 20, 15, 10m
#  	Classes:	Single Op All Band (QRP/Low/High)
# Single Op Single Band (Low/High)
# Single Op All Bands (Low/High)
# Single Op All Bands 24hours (Low/High)
# Multi-Single (Low/High)
# Multi-Multi (Low/High)
# LP: 100 watts

#  	Exchange:	RST + age ( or 01 ) 
#  	Work stations:	Once per band


# < Asian Stations >
#  	QSO Points:	
#           160m band......3 points per Asian QSO. 9 points per Non-Asian QSO.
#           80m band ......2 points per Asian QSO. 6 points per Non-Asian QSO.
#           10m band ......2 points per Asian QSO. 6 points per Non-Asian QSO.
#           Other bands....1 point per Asian QSO. 3 points per Non-Asian QSO.
#       Multipliers:
#           Different entities (according to the DXCC List) worked per band.

# < Non-Asian Stations >
#       QSO Points:     
#           160m band......3 points per Asian QSO. 
#           80m band ......2 points per Asian QSO.
#           10m band ......2 points per Asian QSO.
#           Other bands....1 point per Asian QSO.
#       Multipliers:
#           Different Asian Prefixes

#  	Score Calculation:	Total score = total QSO points x total mults
#  	E-mail logs to:	aacw@jarl.org
#  	Upload log at:  https://contest.jarl.org/upload-aa/	
#  	Mail logs to:	(none)
#  	Find rules at:	https://www.jarl.org/English/4_Library/A-4-3_Contests/aadx_eng.html
#  	Cabrillo name:	ALL-ASIA-CW


import datetime
import logging

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import calculate_wpx_prefix
from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "age (or 01)"

name = "AADX CW"
cabrillo_name = "AADX-CW"
mode = "CW"
# columns = [0, 1, 2, 3, 4, 5, 6, 11, 15]

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
#   "WPX",
    "M1",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2

my_continent = ""
my_country = ""

def init_contest(self):
    """setup plugin"""

    global my_continent
    global my_country
    
    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        my_country = item.get("entity", "")
        my_continent = item.get("continent", "")

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

    global my_continent
    global my_country

    result = self.cty_lookup(self.contact.get("Call", ""))
    band = int(int(float(self.contact.get("Freq", 0))) / 1000)

    if result is not None:
        item = result.get(next(iter(result)))
        their_country = item.get("entity", "")
        their_continent = item.get("continent", "")


    if my_country.upper() == their_country.upper():
        self.contact["IsMultiplier1"] = 0
        return

    if my_continent == "AS": 

        dxcc = self.contact.get("CountryPrefix", "")
        band = self.contact.get("Band", "")
        query = (
            f"select count(*) as dxcc_count from dxlog where "
            f"CountryPrefix = '{dxcc}' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')}"
            f";"
        )
        result = self.database.exec_sql(query)
        if not result.get("dxcc_count", ""):
            self.contact["IsMultiplier1"] = 1
        else:
            self.contact["IsMultiplier1"] = 0

    else:
        if their_continent != "AS":
            self.contact["IsMultiplier1"] = 0
            return 
        
        if self.contact.get("WPXPrefix", ""):
            result = fetch_wpx_exists_before_me(self , self.contact.get("WPXPrefix", "") , self.contact.get("TS", "") , self.contact.get("Band", ""))
            # result = self.database.fetch_wpx_exists(self.contact.get("WPXPrefix", ""))
            if result.get("wpx_count", "") :
                self.contact["IsMultiplier1"] = 0
            else:
                self.contact["IsMultiplier1"] = 1


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    # result = self.database.get_serial()
    # serial_nr = str(result.get("serial_nr", "1")).zfill(3)

    self.other_1.setText(str(self.contest_settings.get("SentExchange", 0)))

def points(self):
    """Calc point"""

    global my_continent
    global my_country

    if self.contact_is_dupe > 0:
        return 0

    result = self.cty_lookup(self.contact.get("Call", ""))
    band = int(int(float(self.contact.get("Freq", 0))) / 1000)
    # print ('band:',band)
    # print ('my_continent:',my_continent)
    if result is not None:
        item = result.get(next(iter(result)))
        their_country = item.get("entity", "")
        their_continent = item.get("continent", "")

        # Both in same country
        if my_country.upper() == their_country.upper():
            return 0

        # Asian Stations
        if my_continent == "AS":
            if their_continent == "AS":
                if band in [1]:
                    return 3
                elif band in [3, 28]:
                    return 2
                else:
                    return 1
            else:
                if band in [1]:
                    return 9
                elif band in [3, 28]:
                    return 6
                else:
                    return 3

        # Non-Asian Stations
        else:
            if their_continent == "AS":
                if band in [1]:
                    return 3
                elif band in [3, 28]:
                    return 2
                else:
                    return 1
            else:
                return 0

    # Something wrong
    return 0


def show_mults(self):
    """Return display string for mults"""

    mult_data = self.database.fetch_mult_count(1)
    mults = int(mult_data.get("count", 0))
    return mults


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    mults = show_mults(self)
    points = get_points(self)
    return points * mults


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "AADX-CW")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Outputs a single line of cabrillo file in the proper encoding."""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
    # 
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
            # if mode in ["SSB+CW", "SSB+CW+DIGITAL"]:
            #     mode = "MIXED"
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
                ops += f"{op.get('Operator', '')}, "
            if self.station.get("Call", "") not in ops:
                ops += f"@{self.station.get('Call','')}"
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
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '')).zfill(2).ljust(6)}",
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

    global my_continent
    global my_country

    all_contacts = self.database.fetch_all_contacts_asc()
    
    if my_continent == "AS":
        for contact in all_contacts:
            self.contact = contact
            contact["Points"] = points(self)
            time_stamp = contact.get("TS", "")
            # dxcc = contact.get("CountryPrefix", "")
            result = self.cty_lookup( contact.get("Call", ""))
            if result is not None:
                item = result.get(next(iter(result)))
                their_country = item.get("entity", "")
                primary_pfx = item.get("primary_pfx", "") 
                contact["CountryPrefix"] = primary_pfx 

                
            band = contact.get("Band", "")
            result = fetch_dxcc_exists_before_me(self,primary_pfx, time_stamp, band)
            dxcc_count = result.get("dxcc_count", 1)
            if dxcc_count == 0 and my_country.upper() != their_country.upper():
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            self.database.change_contact(contact)
    else:  
        for contact in all_contacts:
            self.contact = contact
            contact["Points"] = points(self)
            time_stamp = contact.get("TS", "")
            # wpx = contact.get("WPXPrefix", "")
            wpx =  calculate_wpx_prefix(contact.get("Call", ""))
            contact["WPXPrefix"] = wpx

            result = fetch_wpx_exists_before_me(self, wpx, time_stamp, self.contact.get("Band", ""))
            # wpx_count = result.get("wpx_count", 1)
            if contact["Points"] > 0 and result.get("wpx_count", 1) == 0:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            self.database.change_contact(contact)

def fetch_dxcc_exists_before_me( self,dxcc, time_stamp, band ) -> dict:
    """returns the dict dxcc_count of dxcc existing in current contest."""
    
    contest_nr = self.pref.get("contest")
    
    query = (
        f"select count(*) as dxcc_count from dxlog where "
        f"TS < '{time_stamp}' "
        f"and CountryPrefix = '{dxcc}' "
        f"and Band = '{band}' "
        f"and ContestNR = {contest_nr} "
        f";"
    )
    
    result = self.database.exec_sql(query)
    return result

def fetch_wpx_exists_before_me(self, wpx, time_stamp, band) -> dict:
    """returns a dict key of wpx_count for specific band."""
    contest_nr = self.pref.get("contest")
    
    query = (
        f"select count(*) as wpx_count from dxlog where "
        f" TS < '{time_stamp}' "
        f"and WPXPrefix = '{wpx}' "
        f"and ContestNR = {contest_nr} "
        f"and Band = '{band}' "
        f";"
    )
    
    result = self.database.exec_sql(query)
    return result


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
