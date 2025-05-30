"""10 10 fall cw plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "# or # And Dist"

ukei_pfx = [
    "G",
    "GD",
    "GJ",
    "GM",
    "GI",
    "GW",
    "GU",
    "EI",
]

name = "UKEI-DX"
cabrillo_name = "UKEI-DX"
mode = "BOTH"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 5, 6, 15]
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

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2


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
    self.other_label.setText("Sent Nr")
    self.field2.setAccessibleName("Sent Number")
    self.exch_label.setText("# and Dist")
    self.field4.setAccessibleName("Number and District")


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
    exch = str(self.contest_settings.get("SentExchange", 0))
    result = self.database.get_serial()
    serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(exch.replace("#", serial_nr))


def points(self):
    """Calc point"""

    # UK/EI stations contacting :
    # UK/EI/Europe 80m, 40m - 4 points 20m, 15m, 10m - 2 points
    # DX (Outside Europe) 80m, 40m - 8 points 20m, 15m, 10m - 4 points

    # Note : For UK/EI stations only, all QSOs will score double points between the hours of 0100z and 0459z.

    # European stations contacting :
    # UK/EI 80m, 40m - 4 points 20m, 15m, 10m - 2 points
    # Europe 80m, 40m - 2 points 20m, 15m, 10m - 1 points
    # DX (Outside Europe) 80m, 40m - 4 points 20m, 15m, 10m - 2 points

    # DX (Outside Europe) contacting :
    # UK/EI 80m, 40m - 8 points 20m, 15m, 10m - 4 points
    # Europe 80m, 40m - 4 points 20m, 15m, 10m - 2 points
    # DX (Outside Europe) 80m, 40m - 2 points 20m, 15m, 10m - 1 points

    # f"{primary_pfx}: {continent}/{entity} cq:{cq} itu:{itu}"

    if self.contact_is_dupe > 0:
        return 0

    myprimary_pfx = ""
    # mycountry = ""
    mycontinent = ""
    hisprimary_pfx = ""
    # hiscountry = ""
    hiscontinent = ""

    result = self.cty_lookup(self.station.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        myprimary_pfx = item.get("primary_pfx", "")
        # mycountry = item.get("entity", "")
        mycontinent = item.get("continent", "")

    result = self.cty_lookup(self.contact.get("Call", ""))
    if result is not None:
        item = result.get(next(iter(result)))
        hisprimary_pfx = item.get("primary_pfx", "")
        # hiscountry = item.get("entity", "")
        hiscontinent = item.get("continent", "")

    st = 100
    et = 459
    zt = datetime.datetime.now(datetime.timezone.utc).isoformat(" ")[11:16]
    ct = int(zt[0:2]) * 100 + int(zt[3:5])
    double_window = st <= ct <= et

    # UK/EI stations:
    if myprimary_pfx in ukei_pfx:
        if hiscontinent == "EU":
            if self.contact.get("Band", 0) in ["3.5", "7"]:
                return 4 + (4 * double_window)
            return 2 + (2 * double_window)
        if self.contact.get("Band", 0) in ["3.5", "7"]:
            return 8 + (8 * double_window)
        return 4 + (4 * double_window)

    # European stations:
    if mycontinent == "EU":
        if hisprimary_pfx in ukei_pfx:
            if self.contact.get("Band", 0) in ["3.5", "7"]:
                return 4
            return 2
        elif hiscontinent == "EU":
            if self.contact.get("Band", 0) in ["3.5", "7"]:
                return 2
            return 1
        if self.contact.get("Band", 0) in ["3.5", "7"]:
            return 4
        return 2

    # DX (Outside Europe)
    if mycontinent != "EU":
        if hisprimary_pfx in ukei_pfx:
            if self.contact.get("Band", "") in ["3.5", "7"]:
                return 8
            return 4
        elif hiscontinent == "EU":
            if self.contact.get("Band", "") in ["3.5", "7"]:
                return 4
            return 2
        if self.contact.get("Band", "") in ["3.5", "7"]:
            return 2
        return 1

    return 0


def show_mults(self):
    """Return display string for mults"""

    query = f"SELECT COUNT(DISTINCT CountryPrefix) as dxcc_count FROM DXLOG WHERE CountryPrefix NOT IN ('EI', 'G', 'GD', 'GI', 'GJ', 'GM', 'GU', 'GW') and ContestNR = {self.pref.get('contest', '1')};"
    result = self.database.exec_sql(query)
    dxcc_count = result.get("dxcc_count", 0)

    query = f"SELECT COUNT(DISTINCT SUBSTR(NR, LENGTH(NR) - 1)) as code_count FROM DXLOG WHERE ContestNR = {self.pref.get('contest', '1')}  and typeof(NR) = 'text';"
    result = self.database.exec_sql(query)
    code_count = result.get("code_count", 0)

    return dxcc_count + code_count


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
    gen_adif(self, cabrillo_name)


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
                sentnr = str(contact.get("SentNr", "")).upper().split()
                if len(sentnr) == 2:
                    sentnr = sentnr[0].zfill(3) + " " + sentnr[1]
                else:
                    sentnr = sentnr[0].zfill(3) + " --"

                nr = str(contact.get("NR", "")).upper().split()
                if len(nr) == 2:
                    nr = nr[0].zfill(3) + " " + nr[1]
                else:
                    if nr[0][-2:].isalpha():
                        nr = nr[0][:-2].zfill(3) + " " + nr[0][-2:]
                    else:
                        nr = nr[0].zfill(3) + " --"

                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{sentnr} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{nr}",
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


def get_mults(self):
    """"""

    mults = {}
    return mults


def just_points(self):
    """"""
    return get_points(self)


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
