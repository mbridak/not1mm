"""Ernst Krenkel Memorial"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import


# RAEM Contest
#  	Status:	Active
#  	Geographic Focus:	Worldwide
#  	Participation:	Worldwide
#  	Mode:	    CW
#  	Bands:	    80, 40, 20, 15, 10m
#  	Classes:	Single Op All Band (Low/High)
#               Single Op Single Band
#               Multi-Single
#  	Max power:	HP: >100 watts
#               LP: 100 watts
#  	Exchange:	Serial No. + latitude (degs only) + hemisphere + longitude (degs only) + hemisphere (see rules)
#               N=North, S=South, W=West, O=East (e.g. 57N 85O)
#  	Work stations:	Once per band
#  	QSO Points:	50 points + 1 point for every degree difference in geo location, both latitude and longitude
#               QSO with Polar station: 100 points additional
#               QSO with RAEM Memorial Station: 300 points additional
#  	Multipliers:	Polar stations multiply total QSO points by 1.1
#  	Score Calculation:	Total score = total QSO points
#  	E-mail logs to:	raem[at]srr[dot]ru
#  	Upload log at:	http://ua9qcq.com/
#  	Mail logs to:	(none)
#  	Find rules at:	https://raem.srr.ru/rules/
#  	Cabrillo name:	RAEM

# Label and field names
# callsign_label, callsign
# snt_label, sent
# rcv_label, receive
# other_label, other_1
# exch_label, other_2

# command button names
# esc_stop
# log_it
# mark
# spot_it
# wipe


import datetime
import logging

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "33N117W"

name = "RAEM"
cabrillo_name = "RAEM"
mode = "CW"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "SentNr",
    "RcvNr",
    "Exchange1",
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
    self.field1.show()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("Sent S/N")
    self.sent.setAccessibleName("Sent Serial Number")
    self.other_label.setText("Rcv S/N")
    self.other_1.setAccessibleName("Serial Number")
    self.exch_label.setText("Exchange")
    self.other_2.setAccessibleName("Exchange")
    self.sent.setText("")


def reset_label(self):  # pylint: disable=unused-argument
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.other_1: self.sent,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = "599"
    self.contact["RCV"] = "599"
    self.contact["SentNr"] = self.sent.text()
    self.contact["NR"] = self.other_1.text()
    self.contact["Exchange1"] = self.other_2.text()


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    field = self.sent
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(field.text()) == 0:
        field.setText(serial_nr)


def latlondif(self, exchange1: str):
    """"""
    ourexchange = self.contest_settings.get("SentExchange", None)
    if ourexchange is None:
        return 0, False
    ourexchange = ourexchange.upper()
    if len(exchange1) < 4:
        return 0, False
    exchange1 = exchange1.upper()

    latindex = None
    ourlat = None
    ourlon = None
    if "N" in ourexchange:
        latindex = ourexchange.index("N")
        lat = ourexchange[:latindex]
        if lat.isnumeric():
            ourlat = int(lat)
    if "S" in ourexchange:
        latindex = ourexchange.index("S")
        lat = ourexchange[:latindex]
        if lat.isnumeric():
            ourlat = int(lat)
    if "W" in ourexchange:
        lon = ourexchange[latindex + 1 : ourexchange.index("W")]
        if lon.isnumeric():
            ourlon = int(lon)
    if "O" in ourexchange:
        lon = ourexchange[latindex + 1 : ourexchange.index("O")]
        if lon.isnumeric():
            ourlon = int(lon)
    if ourlat is None or ourlon is None:
        return 0, False

    hislat = None
    hislon = None
    if "N" in exchange1:
        latindex = exchange1.index("N")
        lat = exchange1[:latindex]
        if lat.isnumeric():
            hislat = int(lat)
    if "S" in exchange1:
        latindex = exchange1.index("S")
        lat = exchange1[:latindex]
        if lat.isnumeric():
            hislat = int(lat)
    if "W" in exchange1:
        lon = exchange1[latindex + 1 : exchange1.index("W")]
        if lon.isnumeric():
            hislon = int(lon)
    if "O" in exchange1:
        lon = exchange1[latindex + 1 : exchange1.index("O")]
        if lon.isnumeric():
            hislon = int(lon)
    if hislat is None or hislon is None:
        return 0, False

    return abs(ourlat - hislat) + abs(ourlon - hislon), hislat >= 66


def points(self):
    """Calc point"""
    # 50 points + 1 point for every degree difference in geo location, both latitude and longitude
    # QSO with Polar station: 100 points additional
    # QSO with RAEM Memorial Station: 300 points additional

    if self.contact_is_dupe > 0:
        return 0
    points = 50
    morepoints, ispolar = latlondif(self, self.other_2.text())
    points += morepoints
    if ispolar is not False:
        points += 100
    if self.callsign.text() == "RAEM":
        points += 300

    return points


def show_mults(self):
    """Return display string for mults"""
    ourexchange = self.contest_settings.get("SentExchange", None)
    if ourexchange is None:
        return 0, False
    ourexchange = ourexchange.upper()

    latindex = None
    ourlat = None
    if "N" in ourexchange:
        latindex = ourexchange.index("N")
        lat = ourexchange[:latindex]
        if lat.isnumeric():
            ourlat = int(lat)
    if "S" in ourexchange:
        latindex = ourexchange.index("S")
        lat = ourexchange[:latindex]
        if lat.isnumeric():
            ourlat = int(lat)

    if ourlat is not None:
        if ourlat >= 66:
            return 1.1

    return 1


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
    gen_adif(self, cabrillo_name, "RAEM")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file. Maybe."""
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
                    f"{str(contact.get('SentNr', '')).ljust(6)} "
                    f"{self.contest_settings.get('SentExchange', '').ljust(14).upper()}"
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('NR', '')).ljust(6)}"
                    f"{str(contact.get('Exchange1', '')).ljust(14)} ",
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
    # all_contacts = self.database.fetch_all_contacts_asc()
    # for contact in all_contacts:
    #     time_stamp = contact.get("TS", "")
    #     wpx = contact.get("WPXPrefix", "")
    #     result = self.database.fetch_wpx_exists_before_me(wpx, time_stamp)
    #     wpx_count = result.get("wpx_count", 1)
    #     if wpx_count == 0:
    #         contact["IsMultiplier1"] = 1
    #     else:
    #         contact["IsMultiplier1"] = 0
    #     self.database.change_contact(contact)


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Exch1', '')}, {result.get('UserText','...')}"
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

        elif self.current_widget == "other_1" or self.current_widget == "other_2":
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

        elif self.current_widget == "other_1" or self.current_widget == "other_2":
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


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
