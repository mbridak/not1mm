"""WAG - Worked All Germany plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

#   Worked All Germany Contest
#   Status:	Active
#   Geographic Focus: Germany
#   Participation:	Worldwide
#   Awards:	Worldwide
#   Mode: CW, SSB
#   Bands: 80m, 40m, 20m, 15m, 10m
#   Classes:
#       Single operator, CW, low power
#       Single operator, CW, high power
#       Single operator, SSB, low power (new since 2019)
#       Single operator, SSB, high power (new since 2019)
#       Single operator, mixed, low power
#       Single operator, mixed, high power
#       Single operator, mixed, QRP
#       Multi operator
#       Trainee (Auszubildende): Participiants with trainee callsign. (Prefixes DN1-DN8 and /T stations.)
#   Max power: HP: >100W, LP < 100W, QRP < 5W
#   Exchange: RST + DOK
#       non-Member (DL): RST + 'NM' or 'no member'
#       outside DL: RST + serial number
#   Work stations: Once per band and mode
#   QSO Points:	1 point per QSO
#   Multipliers:
#       DL: DOK (DARC/VFDB), 'NM' does not count + each DXCC/WAE per band
#   Score Calculation:	Total score = total QSO points x total mults
#   Mail logs to: (none)
#   Find rules at:	https://www.darc.de/der-club/referate/conteste/wag-contest/regeln/
#   Upload logs at: https://dxhf2.darc.de/~waglog/upload.cgi?form=referat&lang=de
#   Cabrillo name: WAG


import datetime
import logging
import re

from pathlib import Path

from not1mm.lib.plugin_common import (
    gen_adif,
)  # , imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

__plugin_version__ = "0.1"

EXCHANGE_HINT = "DOK/NM or #"

name = "WAG"
contest_id = "WAG"
cabrillo_name = "WAG"
mode = "BOTH"  # CW SSB BOTH RTTY
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "M1",
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

    # Is the contester located in DL?
    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        if item.get("primary_pfx", "") == "DL":
            self.is_german = True
        else:
            self.is_german = False
    logger.debug(f"Contest station is DL: {self.is_german}")


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.snt_label.setText("SNT")
    self.other_label.setText("DOK/# Sent")
    self.field3.setAccessibleName("RST Sent")
    self.exch_label.setText("DOK/# RCVD")
    self.field4.setAccessibleName("DOK/NM or Number")


def reset_label(self):
    """reset label after field cleared"""

    # Reset the dupe_indicator to his correct text as we used it for warnings.
    self.dupe_indicator.setText("Dupe!")


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
    """Set contact variables and calculate multis"""

    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["NR"] = self.other_2.text()
    self.contact["SentNr"] = self.other_1.text()

    dok = self.contact["NR"].upper()
    dxcc = self.contact.get("CountryPrefix", "")
    band = self.contact.get("Band", "")
    district = get_district(dok)

    # Multiplier
    # non-DL worked DL
    if dxcc == "DL" and not isinstance(dok, int) and dok != "NM" and not self.is_german:
        query = (
            f"select count(*) as dok_count from dxlog where 1=1 "
            f"and NR like '{district}%' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        logger.debug(query)
        result = self.database.exec_sql(query)
        logger.debug(result)
        count = int(result.get("dok_count", 0))
        if count == 0:
            self.contact["IsMultiplier1"] = 1
            logger.debug(f"{self.contact.get('all')} is a Multi")
        else:
            self.contact["IsMultiplier1"] = 0
            logger.debug(f"{self.contact.get('Call')} is not a Multi")

    # Multiplier
    # DL worked any station
    if self.is_german:
        query = (
            f"select count(*) as dxcc_count from dxlog where 1=1 "
            f"and CountryPrefix = '{dxcc}' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        logger.debug(query)
        result = self.database.exec_sql(query)
        logger.debug(result)
        count = int(result.get("dxcc_count", 0))
        if count == 0:
            self.contact["IsMultiplier1"] = 1
            logger.debug(f"{self.contact.get('Call')} is a Multi")
        else:
            self.contact["IsMultiplier1"] = 0
            logger.debug(f"{self.contact.get('Call')} is not a Multi")


def predupe(self):
    """prefill his exchange with last known values"""

    # Check if the typed in callsign should be worked (DL only in WAG for non-DL stations!)
    dxcc = self.contact.get("CountryPrefix", "")
    if not self.is_german and dxcc != "DL":
        logger.debug("DL only in WAG!")
        self.dupe_indicator.setText("DL stations only!")
        self.dupe_indicator.show()


def prefill(self):
    """Fill SentNR"""
    sent_sxchange_setting = self.contest_settings.get("SentExchange", "")
    if sent_sxchange_setting.strip() == "#":
        result = self.database.get_serial()
        serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(self.other_1.text()) == 0:
            self.other_1.setText(serial_nr)
    else:
        self.other_1.setText(sent_sxchange_setting)

    if self.other_2.text() == "":
        call = self.callsign.text().upper()
        query = f"select NR from dxlog where Call = '{call}' and ContestName = '{contest_id}' order by ts desc;"
        logger.debug(query)
        result = self.database.exec_sql(query)
        logger.debug("%s", f"{result}")
        if result:
            if isinstance(result.get("NR", ""), str):
                self.other_2.setText(str(result.get("NR", "")))


def points(self):
    """Calculate points"""

    # Dupe
    if self.contact_is_dupe > 0:
        return 0

    # non-DL worked DL
    # non-DL worked non-DL
    # DL worked DL
    # DL worked EU
    # DL worked DX
    if not self.is_german and self.contact.get("CountryPrefix", "") == "DL":
        return 3
    elif not self.is_german and self.contact.get("CountryPrefix", "") != "DL":
        return 0
    elif self.is_german and self.contact.get("CountryPrefix", "") == "DL":
        return 1
    elif self.is_german and self.contact.get("Continent", "") == "EU":
        return 3
    elif self.is_german and self.contact.get("Continent", "") != "EU":
        return 5
    else:
        return 0


def show_mults(self):
    """Return number of multis"""
    result = self.database.fetch_mult_count(1)
    if result:
        return int(result.get("count", 0))
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
    gen_adif(self, cabrillo_name, contest_id)


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
                f"CREATED-BY: Not1MM v{__version__} - WAG-Contest-Plugin v{__plugin_version__} by DL6CQ",
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

    all_contacts = self.database.fetch_all_contacts_asc()
    if not all_contacts:
        return

    for contact in all_contacts:

        contact["IsMultiplier1"] = 0

        time_stamp = contact.get("TS", "")
        dok = contact.get("NR", "")
        dxcc = contact.get("CountryPrefix", "")
        band = contact.get("Band", "")
        district = get_district(str(dok))

        # Multiplier
        # non-DL worked DL
        if (
            dxcc == "DL"
            and not isinstance(dok, int)
            and dok != "NM"
            and not self.is_german
        ):
            query = (
                f"select count(*) as dok_count from dxlog where 1=1 "
                f"and TS < '{time_stamp}' "
                f"and NR like '{district}%' "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            logger.debug(query)
            result = self.database.exec_sql(query)
            logger.debug(result)
            count = int(result.get("dok_count", 0))
            if count == 0:
                contact["IsMultiplier1"] = 1
                logger.debug(f"{contact.get('Call')} is a Multi")
            else:
                contact["IsMultiplier1"] = 0
                logger.debug(f"{contact.get('Call')} is not a Multi")

        # Multiplier
        # DL worked any station
        if self.is_german:
            query = (
                f"select count(*) as dxcc_count from dxlog where 1=1 "
                f"and TS < '{time_stamp}' "
                f"and CountryPrefix = '{dxcc}' "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            logger.debug(query)
            result = self.database.exec_sql(query)
            count = int(result.get("dxcc_count", 0))

            if count == 0:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0

        self.database.change_contact(contact)
    trigger_update(self)


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

    # print(f"checking esm {self.current_widget=} {with_enter=} {self.pref.get('run_state')=}")

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

        elif self.current_widget in ["other_1", "other_2"]:
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

        elif self.current_widget in ["other_1", "other_2"]:
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


def populate_history_info_line(self):
    """Show history info if available"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Exch1', '')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText','')}")
        if self.other_2.text() == "":
            # Strip leading whitespace for the case that historyfile is not
            # well formatted, f.e. CA0LL, DOK instead of CA0LL,DOK
            self.other_2.setText(f"{result.get('Exch1', '').lstrip()}")


# def get_mults(self):
#     """Get mults for RTC XML"""
#     mults = {}
#     mults["state"], mults["wpxprefix"] = show_mults(self, rtc=True)
#     return mults


def trigger_update(self):
    """Triggers the log window to update."""
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if self.log_window:
        self.log_window.msg_from_main(cmd)


def get_district(dok):
    """
    Get first letter of received DOK (Distrikt)
    With a SDOK (special DOK) we need the first letter (not character!) of the
    SDOK as multi.

    :param dok: a DOK or special DOK
    :type  dok: string
    :return: district - one letter for the DARC district
    :rtype: string
    """

    district = re.search(r"[A-Za-z]", dok)
    if district:
        return district.group(0)
    return None
