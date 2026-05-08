"""Dutch PACC Contest"""

"""
6. Exchange:
6.1 Non-Dutch (Non-PA) stations: signal report + QSO number, starting with 001.
6.1.1 Non-Dutch (Non-PA) MOAB (Multi Op, All Bands) stations can use separate serial numbers for each band if using
more than one transmitter at a time. If only one transmitter at a time is used, chronological serial numbers need to be used,
but skipped numbers are allowed (e.g. as a result of blocking numbers for the multiplier station).
6.2 Dutch (PA) stations: signal report + province code (two letters).
There are 12 provinces: DR, FL, FR, GD, GR, LB, NB, NH, OV, UT, ZH and ZL
7. QSO Points
7.1 Each valid contact with another participating contest station is worth one (1) point. For foreign stations: only contacts
with Dutch (PA) stations count. In MIXED mode (CW/SSB) a valid qso counts once per mode per band. For PA stations:
cross contest contacts (e.g. if the PACC coincides with the RSGB 160m contest) are considered valid as long as a serial
number is received. No cross mode or cross band contacts are allowed.
7.2 SWL stations count each individual heard PACC contest station (both Dutch (PA) and non-Dutch (Non-PA)) as 1 point
provided both the calls and the exchange number of the heard station (i.e. RST + number or RST + Province) is logged of
the QSO of concern. Each call counts only once per band, per mode and one particular contest station may not be logged
as counter station more than 10 times per band.
7.2.1 All SWL QSO’s should be logged during the contest.
8. Dupes
8.1 Dupes are contacts made with the same station on the same band. If the first contact between stations is valid, dupes
have 0 points value. If the first contact is not valid, the second (dupe) contact is accepted.
8.2 DO NOT DELETE DUPES! Dupe contacts are not penalized; one does not have to mark them in the Cabrillo log
submission.
Moreover, entrants are strongly recommended to leave DUPES in the log file.
9. Multipliers
9.1 Non-Dutch (Non-PA) stations (incl. SWL stations): a multiplier of one (1) for each different Dutch (PA) province
contacted on each band on each mode.
The Dutch (PA) province abbreviations are:
DR = Drenthe NB = Noord-Brabant
FL = Flevoland NH = Noord-Holland
FR = Friesland OV = Overijssel
GD = Gelderland UT = Utrecht
GR = Groningen ZH = Zuid-Holland
LB = Limburg ZL = Zeeland
9.2 Dutch (PA) stations (incl. SWL stations):
• A multiplier of one (1) for each different DXCC entity (ARRL list) on each band, each mode including PA, with the
following exceptions:
• A multiplier of one (1) for each different call area of Asiatic Russia (UA8/9/0), Chile (CE), Japan (JA), Argentina (LU),
Brazil (PY), Canada (VE), USA, Australia (VK), South Africa (ZS) and New-Zealand (ZL) on each band, each mode.
Note 1: this means that Asiatic Russia has 3 call areas/multipliers: UA8, UA9 and UA0. Canadian call areas are interpreted
as geographical districts, which means VE1, VO1, VY1, VE2, VO2, VY2, VY0 are all separate multipliers, but e.g. VE2,
CG2, XK2 are all the same multiplier (VE2).
Note 2: A reciprocal call sign in one of the countries which have call areas as multipliers, but without a call area designation,
is counted as the zero-call area, e.g. LU/G3XYZ gives multiplier LU0. Reciprocal calls in W, JA, VE and UA need to indicate
their call area, otherwise the call should be regarded as invalid, e.g. W3/DL8ABC is valid, W/DL8ABC is invalid. (This
means that, theoretically, PY0 is a separate multiplier besides PY0F, PY0S and PY0T).
Note 3: Call areas are taken as-is from the call sign, even if it is known that the station is located in a different area,
UNLESS the station explicitly indicates it. E.g. K5ZD is multiplier W5, but K5ZD/1 would give multiplier W1.
Note 4: Special call signs will count for the call area to which they geographically belong (e.g. UE150SBM = UA0).
"""

"""
Test calls

PA2WRD             PA3ADU             PA3AKP             PA3ARM
PA3BGQ             PA3BQP             PA3BQS             PA3CDD
PA3CSG             PA3CXB              PA3DB             PA3DNA
PA3DRL             PA3DSB             PA3DTR             PA3DUU
PA3DVA             PA3DWJ             PA3EEG             PA3EKM
PA3ELQ              PA3EM             PA3EMN             PA3EOU
PA3EOZ             PA3EPO             PA3EVY             PA3EWG
PA3FUJ             PA3FZV             PA3GDD             PA3GEO
PA3GMM  
"""
# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import datetime
import logging

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "# or Province"

name = "PACC"
cabrillo_name = "PACC"
mode = "BOTH"  # CW SSB BOTH RTTY

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
dupe_type = 3


PROV_SEC = [
    "DR",
    "FL",
    "FR",
    "GD",
    "GR",
    "LB",
    "NB",
    "NH",
    "OV",
    "UT",
    "ZH",
    "ZL",
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
    self.exch_label.setText("Prov or SN")
    self.field4.setAccessibleName("Province code or Serial Number")


def reset_label(self):
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


def validate(self):
    """doc"""
    return True


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["NR"] = self.other_2.text().upper()
    self.contact["SentNr"] = self.other_1.text()


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill sentnr"""
    # result = self.database.get_serial()
    # serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"

    exchange = self.contest_settings.get("SentExchange", "").replace("#", serial_nr)
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exchange)


def points(self):
    """Calc point"""

    # Each valid contact with another participating contest station is worth one (1) point. For foreign stations: only contacts
    # with Dutch (PA) stations count. In MIXED mode (CW/SSB) a valid qso counts once per mode per band. For PA stations:
    # cross contest contacts (e.g. if the PACC coincides with the RSGB 160m contest) are considered valid as a long as a serial
    # number is received. No cross mode or cross band contacts are allowed.

    if self.contact_is_dupe > 0:
        return 0

    # Am I a dutch station.
    im_dutch = False
    theyre_dutch = False

    my_exchange = str(self.contest_settings.get("SentExchange", 0))
    if my_exchange.isalpha():
        im_dutch = True

    their_exchange = self.other_2.text().upper()
    if their_exchange.isalpha():
        theyre_dutch = True

    if im_dutch:
        return 1
    else:
        if theyre_dutch:
            return 1

    return 0


def im_dutch(self):
    my_exchange = str(self.contest_settings.get("SentExchange", 0))
    if my_exchange.isalpha():
        return True
    return False


def show_mults(self):
    """Return display string for mults"""

    sql = ""
    if im_dutch(self) is False:
        sql = f"select count(DISTINCT(NR || ':' || Band || ':' || Mode)) as mult_count from dxlog where ContestNR = {self.database.current_contest} and NR in ('DR','FL','FR','GD','GR','LB','NB','NH','OV','UT','ZH','ZL');"
    else:
        sql = f"select count(DISTINCT(CountryPrefix || ':' || Band || ':' || Mode)) as mult_count from dxlog where ContestNR = {self.database.current_contest};"

    result = self.database.exec_sql(sql)
    if result:
        return result.get("mult_count", 0)
    return 0


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    mults = show_mults(self)
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        if int(mults) > 0:
            contest_points = int(score) * (int(mults) + 1)
            return contest_points
        contest_points = int(score)
        return contest_points
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "PACC")


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
                if themode in ("LSB", "USB", "AM", "FM"):
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

        elif self.current_widget in ["other_1", "other_2"]:
            if self.other_1.text() == "" or self.other_2.text() == "":
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
            if self.other_1.text() == "" or self.other_2.text() == "":
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


def get_mults(self):
    """"""

    mults = {}
    mults["state"] = show_mults(self)
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


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Sect', '')}, {result.get('UserText','...')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        # if self.other_1.text() == "":
        #     self.other_1.setText(f"{result.get('Exch1', '')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Sect', '')}")
