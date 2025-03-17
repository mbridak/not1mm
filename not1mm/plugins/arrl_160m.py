"""ARRL 160 CW plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import, line-too-long

import datetime
import logging
import platform

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "ST/Prov or DX CQ Zone"

name = "ARRL 160-Meter"
cabrillo_name = "ARRL-160"
mode = "CW"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "PFX",
    "Exchange1",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 1


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
    self.snt_label.setText("SNT")
    self.field1.setAccessibleName("RST Sent")
    self.exch_label.setText("ARRL/RAC Section")
    self.field4.setAccessibleName("Received Exchange")


def reset_label(self):  # pylint: disable=unused-argument
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_2,
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
        self.other_2: self.receive,
    }


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.contest_settings.get("SentExchange", 0)
    self.contact["Exchange1"] = self.other_2.text()


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""


def points(self):
    """Calc point"""
    # Each contact between W/VE stations counts for two (2) QSO points. Each contact with a DX station counts five (5) QSO points
    call = self.contact.get("Call", "")
    dupe_check = self.database.check_dupe(call)
    if dupe_check.get("isdupe", 0) > 0:
        return 0
    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        for item in result.items():
            mypfx = item[1].get("primary_pfx", "")
            # mycountry = item[1].get("entity", "")
            # mycontinent = item[1].get("continent", "")

    result = self.cty_lookup(self.contact.get("Call", ""))
    if result:
        for item in result.items():
            pfx = item[1].get("primary_pfx", "")
            # entity = item[1].get("entity", "")
            # continent = item[1].get("continent", "")

    # Both in same country

    # 2.1.1 Alaska (KL7 – AK) and Hawaii (KH6 – PAC), the Caribbean US possessions (KP1-KP5 -
    # PR or VI), and all of the Pacific Ocean territories (KHØ-KH9 – PAC) participate as W/VE stations
    # and count as ARRL sections.
    if mypfx in [
        "K",
        "KL",
        "KH0",
        "KH1",
        "KH2",
        "KH3",
        "KH4",
        "KH5",
        "KH6",
        "KH7",
        "KH8",
        "KH9",
        "KP1",
        "KP2",
        "KP3",
        "KP4",
        "KP5",
        "VE",
    ] and pfx in [
        "K",
        "KL",
        "KH0",
        "KH1",
        "KH2",
        "KH3",
        "KH4",
        "KH5",
        "KH6",
        "KH7",
        "KH8",
        "KH9",
        "KP1",
        "KP2",
        "KP3",
        "KP4",
        "KP5",
        "VE",
    ]:
        return 2

    if mypfx.upper() != pfx.upper():
        return 5

    return 0


def show_mults(self):
    """Return display string for mults"""
    mults = 0
    if can_claim_dxcc(self):
        result = self.database.fetch_country_count()
        mults = int(result.get("dxcc_count", 0))

    result = self.database.fetch_exchange1_unique_count()
    mults2 = int(result.get("exch1_count", 0))

    return mults + mults2


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    mults = 0
    result = self.database.fetch_points()
    if result is not None:
        score = result.get("Points", "0")
        if score is None:
            score = "0"
        contest_points = int(score)

        if can_claim_dxcc(self):
            result = self.database.fetch_country_count()
            mults = int(result.get("dxcc_count", 0))

        result = self.database.fetch_exchange1_unique_count()
        mults2 = int(result.get("exch1_count", 0))
        return contest_points * (mults + mults2)
    return 0


def can_claim_dxcc(self):
    """"""
    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        mypfx = ""
        for item in result.items():
            mypfx = item[1].get("primary_pfx", "")
        if mypfx in [
            "K",
            "KL",
            "KH0",
            "KH1",
            "KH2",
            "KH3",
            "KH4",
            "KH5",
            "KH6",
            "KH7",
            "KH8",
            "KH9",
            "KP1",
            "KP2",
            "KP3",
            "KP4",
            "KP5",
            "VE",
        ]:
            return True
        return False


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "ARRL 160-Meter")


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
                frequency = str(int(contact.get("Freq", "0"))).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                thesentnr = contact.get("SentNr", "---")
                if thesentnr == "":
                    thesentnr = "---"
                theexch = contact.get("Exchange1", "---")
                if theexch == "":
                    theexch = "---"

                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(thesentnr).ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(theexch).ljust(6)}",
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
    #     if contact.get("CountryPrefix", "") == "K":
    #         query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = 'K' and Exchange1 = '{contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
    #         result = self.database.exec_sql(query)
    #         if result.get("count", 0) == 0:
    #             contact["IsMultiplier1"] = 1
    #         else:
    #             contact["IsMultiplier1"] = 0
    #         self.database.change_contact(contact)
    #         continue
    #     if contact.get("CountryPrefix", "") == "VE":
    #         query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = 'VE' and Exchange1 = '{contact.get('Exchange1', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
    #         result = self.database.exec_sql(query)
    #         if result.get("count", 0) == 0:
    #             contact["IsMultiplier1"] = 1
    #         else:
    #             contact["IsMultiplier1"] = 0
    #         self.database.change_contact(contact)
    #         continue
    #     query = f"select count(*) as count from dxlog where TS < '{time_stamp}' and CountryPrefix = '{contact.get('CountryPrefix', '')}' and ContestNR = '{self.pref.get('contest', '0')}'"
    #     result = self.database.exec_sql(query)
    #     if result.get("count", 0) == 0:
    #         contact["IsMultiplier1"] = 1
    #     else:
    #         contact["IsMultiplier1"] = 0
    #     self.database.change_contact(contact)
    # trigger_update(self)


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
            if self.contact.get("CountryPrefix", "") in ["K", "VE"]:
                if self.other_2.text() == "":
                    self.make_button_green(self.esm_dict["AGN"])
                    buttons_to_send.append(self.esm_dict["AGN"])
                else:
                    self.make_button_green(self.esm_dict["QRZ"])
                    buttons_to_send.append(self.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
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
            if self.contact.get("CountryPrefix", "") in ["K", "VE"]:
                if self.other_2.text() == "":
                    self.make_button_green(self.esm_dict["AGN"])
                    buttons_to_send.append(self.esm_dict["AGN"])
                else:
                    self.make_button_green(self.esm_dict["EXCH"])
                    buttons_to_send.append(self.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

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
    if can_claim_dxcc(self):
        mults["country"] = self.database.fetch_country_count().get("dxcc_count", 0)

    mults["state"] = self.database.fetch_exchange1_unique_count().get("exch1_count", 0)

    return mults


def just_points(self):
    """"""
    return self.database.fetch_points().get("Points", "0")
