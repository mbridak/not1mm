""" """

import logging
import platform
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import (
    gen_adif,
    get_points,
)

from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "#"

name = "ES FIELD DAY"
cabrillo_name = "ES-FIELD-DAY"
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

# 5 Contest specific dupe check.
dupe_type = 5

estonian_regions = [
    "HM",
    "HR",
    "IV",
    "JG",
    "JR",
    "LN",
    "LV",
    "PL",
    "PU",
    "RP",
    "SR",
    "TA",
    "TL",
    "VC",
    "VO",
    "VP",
]


def specific_contest_check_dupe(self, call):
    """"""
    # get mode from radio state
    mode = self.radio_state.get("mode", "")
    """Dupe checking specific to just this contest."""
    # constant to split the contest - correct ES Open Contest length is 4 hours
    contest_length_in_minutes = 90
    split_contest_by_minutes = 30

    period_count = int(contest_length_in_minutes / split_contest_by_minutes)

    # think about generic solution by splitting the contest to n different periods
    start_date_init = self.contest_settings.get("StartDate", "")
    start_date_init_date = datetime.strptime(start_date_init, "%Y-%m-%d %H:%M:%S")

    # Create time periods dynamically based on period count
    time_periods = []
    for i in range(period_count):
        minutes_to_add = split_contest_by_minutes * (i + 1)
        time_period = start_date_init_date + timedelta(minutes=minutes_to_add)
        time_periods.append(time_period)

    # Assign to variables for backwards compatibility
    time_period_1 = time_periods[0] if len(time_periods) > 0 else None
    time_period_2 = time_periods[1] if len(time_periods) > 1 else None
    time_period_3 = time_periods[2] if len(time_periods) > 2 else None

    # get current time in UTC
    iso_current_time = datetime.now(timezone.utc)
    current_time = iso_current_time.replace(tzinfo=None)

    result = {}
    result["isdupe"] = False

    if (
        time_period_1 is not None
        and current_time < time_period_1
        and current_time >= start_date_init_date
    ):

        result = self.database.check_dupe_on_period_mode(
            call,
            self.contact.get("Band", ""),
            mode,
            start_date_init_date,
            time_period_1.strftime("%Y-%m-%d %H:%M:%S"),
        )

    if (
        time_period_1 is not None
        and time_period_2 is not None
        and current_time < time_period_2
        and current_time >= time_period_1
    ):

        result = self.database.check_dupe_on_period_mode(
            call,
            self.contact.get("Band", ""),
            mode,
            time_period_1.strftime("%Y-%m-%d %H:%M:%S"),
            time_period_2.strftime("%Y-%m-%d %H:%M:%S"),
        )

    if (
        time_period_2 is not None
        and time_period_3 is not None
        and current_time < time_period_3
        and current_time >= time_period_2
    ):

        result = self.database.check_dupe_on_period_mode(
            call,
            self.contact.get("Band", ""),
            mode,
            time_period_2.strftime("%Y-%m-%d %H:%M:%S"),
            time_period_3.strftime("%Y-%m-%d %H:%M:%S"),
        )

    # just for band and mode if outside of time period
    else:
        result = self.database.check_dupe_on_band_mode(
            call, self.contact.get("Band", ""), mode
        )

    return result


def init_contest(self):
    """setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.other_label.setText("Sent")
    self.field3.setAccessibleName("Sent")
    self.exch_label.setText("SN")
    self.field4.setAccessibleName("SN")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.other_1,
        self.sent: self.other_1,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.callsign,
        self.other_1: self.callsign,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text().upper()
    self.contact["NR"] = self.other_2.text().upper()

    self.contact["IsMultiplier1"] = 0
    self.contact["IsMultiplier2"] = 0


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""

    sent_sxchange_setting = self.contest_settings.get("SentExchange", "")
    if sent_sxchange_setting.strip() == "#":
        result = self.database.get_serial()
        serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        # get station region code from setup ARRLSection field
        serial_nr = serial_nr + " " + self.station.get("State", "")

        if serial_nr == "None":
            serial_nr = "001"
        if len(self.other_1.text()) == 0:
            self.other_1.setText(serial_nr)
    else:
        self.other_1.setText(sent_sxchange_setting)


def points(self):
    """ """
    if self.contact_is_dupe > 0:
        return 0

    # get received number and region code

    check_call = self.contact.get("Call", "")
    # all stations with /p give 3 points
    if "/p" in check_call.lower():
        return 3
    # all stations with /qrp give 5 points
    elif "/qrp" in check_call.lower():
        return 5
    else:
        return 1


def show_mults(self, rtc=None):
    """Return display string for mults"""

    # implement here multipliers checks
    # get received number and region code

    # call_result never used, so commenting it out.
    # call_result = str(self.contact.get("NR", ""))
    # create placeholders
    placeholders = ",".join(["?"] * len(estonian_regions))
    # main query to filter by regions
    query = f"SELECT count(distinct(SUBSTR(NR, -2)) || ':' || Band || ':' || Mode) as mults from DXLOG where ContestNR = {self.pref.get('contest', '1')} AND CountryPrefix = 'ES' AND NR GLOB '*[A-Z]*' AND substr(NR,-2) IN ({placeholders});"
    # apply params
    params = estonian_regions
    # run query
    result = self.database.exec_sql_params_mult(query, params)
    if result:
        mult_count = result.get("mults", 0)
        return mult_count
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
        return contest_points * (mults + 1)
    return 0


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "ES OPEN")


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
    now = datetime.now()
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


# def populate_history_info_line(self):
#     result = self.database.fetch_call_history(self.callsign.text())
#     if result:
#         self.history_info.setText(
#             f"{result.get('Call', '')}, {result.get('Exch1', '')}, {result.get('UserText','...')}"
#         )
#     else:
#         self.history_info.setText("")


# def check_call_history(self):
#     """"""
#     result = self.database.fetch_call_history(self.callsign.text())
#     print(f"{result=}")
#     if result:
#         self.history_info.setText(f"{result.get('UserText','')}")
#         if self.other_2.text() == "":
#             self.other_2.setText(f"{result.get('Exch1', '')}")


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

        elif self.current_widget == "other_2":
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

        elif self.current_widget == "other_2":
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


# def get_mults(self):
#     """Get mults for RTC XML"""
#     mults = {}
#     mults["country"], mults["state"] = show_mults(self, rtc=True)
#     return mults


# def just_points(self):
#     """Get points for RTC XML"""
#     return get_points(self)
