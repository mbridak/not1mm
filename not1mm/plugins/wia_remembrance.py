"""
WIA-REMEMBRANCE

Find rules at: https://www.wia.org.au/members/contests/rdcontest/
"""

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import band_mhz_of
from not1mm.lib.plugin_common import contest_time, gen_adif, get_points, imp_adif
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

assert imp_adif

EXCHANGE_HINT = "Years Licenced"
SOAPBOX_HINT = """ 
Exchange: A valid exchange consists of RS(T) followed by a number as follows:

a. For a single operator, the number of years you have been a licenced Ham. For example, if this is your 1st year as a ham then you will sign RS(T) 001. Round off to the nearest whole number. All zeros are not accepted.

b. For a multi-op or club station, the number of licenced years of the longest licenced Amateur present at the start of the contest.

A station may be worked once per band every three hours.  FM counts as SSB and RTTY counts as CW, so the call does stay lit as a dupe across those pairs.
"""

name = "WIA REMEMBRANCE"
cabrillo_name = "WIA-REMEMBRANCE"
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
dupe_type = 5


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
    self.field3.hide()
    self.field4.show()
    self.other_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "Sent"))
    self.other_1.setAccessibleName("Sent")
    self.exch_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "Years Licenced")
    )
    self.other_2.setAccessibleName("Years Licenced")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.other_2,
        self.receive: self.other_2,
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


def prefill(self):
    """Fill SentNR"""
    sent_sxchange_setting = self.contest_settings.get("SentExchange", "")
    if sent_sxchange_setting.strip() == "#":
        # result = self.database.get_serial()
        # serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        serial_nr = str(self.current_sn).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.other_1.text()) == 0:
            self.other_1.setText(serial_nr)
    else:
        self.other_1.setText(sent_sxchange_setting)


def show_mults(self):
    """Return display string for mults"""
    return 0


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "WIA-REMEMBRANCE")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Output a line in the proper file encoding."""
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
    now = datetime.datetime.now(datetime.UTC)
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
                if themode in ("LSB", "USB", "FM"):
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
                frequency = str(round(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '0')).rjust(3, '0').ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '')).rjust(3, '0').ljust(6)}",
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


def check_call_history(self):
    """Check call history database for contact info."""
    # result = self.database.fetch_call_history(self.callsign.text())
    # if result:
    #     self.history_info.setText(f"{result.get('UserText', '')}")
    #     if self.other_2.text() == "":
    #         self.other_2.setText(f"{result.get('Exch1', '')}")


def predupe(self):
    """called after callsign entered"""


def points(self):
    """
    Scoring:
    1. On 160 metres two points per completed valid contact.
    2. On 23cm or higher bands two points per completed valid contact.
    3. On all other bands one point. (no WARC bands allowed)
    4. On CW and RTTY, irrespective of band, double points.
    5. All QSO's logged between 0100 and 0600 LOCAL TIME score triple points.
    """
    if self.contact_is_dupe > 0:
        return 0

    score = 1

    # The band was compared to the string "1.8" while the column holds the
    # float 1.8, so a 160m contact never got its extra point.
    band = band_mhz_of(self.contact.get("Band", 0))
    if band == 1.8:
        score += 1
    if band >= 1240.0:
        score += 1
    if self.contact.get("Mode", "") in (
        "CW",
        "CW-U",
        "CW-L",
        "CWR",
        "RTTY",
        "RTTY-R",
        "LSB-D",
        "USB-D",
        "AM-D",
        "FM-D",
        "DIGI-U",
        "DIGI-L",
        "DIG",
        "RTTYR",
        "PKTLSB",
        "PKTUSB",
        "FSK",
        "PKT",
    ):
        score *= 2
    # Rule 5: a contact between 0100 and 0600 local time scores triple.  The
    # comparison was the wrong way round - `100 >= X <= 600` is "X <= 100" -
    # and it read the wall clock instead of the contact's own time, so a
    # re-scored log used the time of the re-score.
    local = contest_time(self).replace(tzinfo=datetime.timezone.utc).astimezone()
    if 100 <= int(local.strftime("%H%M")) <= 600:
        score *= 3

    return score


def calc_score(self):
    """Return calculated score"""
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)
        return contest_points
    return 0


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Exch1', '')}, {result.get('UserText', '...')}"
        )
    else:
        self.history_info.setText("")


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
                self.esm_call_sent = ""
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
                # If the operator corrected a busted callsign after the
                # exchange was already sent, resend the corrected call
                # ahead of the QRZ/TU macro so the other station logs the
                # right callsign before the QSO is wiped.
                if (
                    self.pref.get("esm_send_corrected_call")
                    and self.esm_call_sent
                    and self.callsign.text() != self.esm_call_sent
                ):
                    self.make_button_green(self.esm_dict["HISCALL"])
                    buttons_to_send.append(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        self.save_contact()
                        self.esm_call_sent = ""
                        continue
                    if button == self.esm_dict.get("HISCALL"):
                        self.esm_call_sent = self.callsign.text()
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


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["state"] = show_mults(self)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)


def date_string_difference(date_str1, date_str2):
    """
    Compare two datetime strings and return the difference
    between the two in %H%M format
    """

    date_format = "%Y-%m-%d %H:%M:%S"

    # Both stamps are UTC as logged; astimezone() on a naive datetime would
    # read them as local time and shift the difference by the local offset.
    dt1 = datetime.datetime.strptime(date_str1, date_format)
    dt2 = datetime.datetime.strptime(date_str2, date_format)
    diff = abs(dt1 - dt2)

    # Extract total seconds to calculate hours and minutes
    total_seconds = int(diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}{minutes:02d}"


def _dupe_mode(mode: str) -> str:
    """Group a mode the way rule 9.3a groups them for the three-hour window.

    FM and SSB count as one mode, and CW and RTTY count as another.
    """
    mode = str(mode).upper()
    if mode in ("LSB", "USB", "SSB", "FM", "AM"):
        return "PH"
    if mode.startswith("CW") or mode.startswith("RTTY"):
        return "CW"
    return mode


def specific_contest_check_dupe(self, call):
    """
    Calculates if call has been worked in current band/mode within 3hrs.

    Rule 9.3a: FM and SSB count as one mode and CW and RTTY as another, so a
    station worked on FM is a duplicate if it is then worked on SSB inside the
    window.  Matching the mode exactly let those pairs score again.
    """
    mode_group = _dupe_mode(self.radio_state.get("mode", ""))

    # get latest QSO w/ same band and mode group.
    query = (
        "select TS from DXLOG where Band = ? and Call = ? and ContestNR = ? and "
        "CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH' "
        "WHEN Mode like 'CW%' or Mode like 'RTTY%' THEN 'CW' ELSE Mode END = ? "
        "order by TS DESC;"
    )
    result = self.database.exec_sql(
        query,
        (
            self.contact.get("Band", ""),
            call,
            self.pref.get("contest", "0"),
            mode_group,
        ),
    )
    if result:
        log_dt = result.get("TS", False)
        if log_dt is not False:
            # The window is measured back from the contact's own time, not
            # the wall clock, so a re-scored or imported log is checked
            # against the clock it was logged on.
            date_time = contest_time(self).strftime("%Y-%m-%d %H:%M:%S")
            delta = date_string_difference(log_dt, date_time)
            if int(delta) < 300:
                return {"isdupe": True}
    return {"isdupe": False}
