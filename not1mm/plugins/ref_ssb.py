"""
REF Contest, SSB
Status:	Active
Geographic Focus:	France + overseas territories
Participation:	Worldwide
Awards:	Worldwide
Mode:	CW
Bands:	80, 40, 20, 15, 10m
Classes:	Single Op All Band
            Single Op Single Band
            Multi-Single
            Club
            SWL
Max power:	HP: >100 Watts
            LP: 100 Watts
            QRP: 5 Watts

Exchange:	French: RST + Department/Prefix
            non-French: RST + Serial No.

Work stations:	Once per band

QSO Points:	French: 6 points per QSO with French station same continent
            French: 15 points per QSO with French station on different continent
            French: 1 point per QSO with non-French station same continent
            French: 2 points per QSO with non-French station on different continent
            non-French: 1 point per QSO with French station same continent
            non-French: 3 points per QSO with French station on different continent

Multipliers:	French/Corsica departments once per band
                French overseas prefixes once per band
                non-French DXCC countries once per band (available only to French stations)

Score Calculation:	Total score = total QSO points x total mults

Upload log at:	https://concours.r-e-f.org/contest/logs/upload-form/
Find rules at:	https://concours.r-e-f.org/reglements/actuels/reg_cdfhfdx.pdf
Cabrillo name:	REF-SSB
Cabrillo name aliases:	REF
"""

import datetime
import logging
import platform

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points

from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Canton or #"

name = "French REF DX contest - SSB"
cabrillo_name = "REF-SSB"
mode = "SSB"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "M1",
    "M2",
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
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    label = self.field3.findChild(QtWidgets.QLabel)
    label.setText("Sent")
    self.field3.setAccessibleName("Sent")
    label = self.field4.findChild(QtWidgets.QLabel)
    label.setText("Dep/Pfx/SN")
    self.field4.setAccessibleName("Department, Prefix or SN")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.field3.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
        self.field2.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
        self.field3.findChild(QtWidgets.QLineEdit): self.field4.findChild(
            QtWidgets.QLineEdit
        ),
        self.field4.findChild(QtWidgets.QLineEdit): self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.field4.findChild(QtWidgets.QLineEdit),
        self.field1.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field2.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field3.findChild(QtWidgets.QLineEdit): self.callsign,
        self.field4.findChild(QtWidgets.QLineEdit): self.field3.findChild(
            QtWidgets.QLineEdit
        ),
    }


def set_contact_vars(self):
    """
    Contest Specific
    Multipliers:
    French/Corsica departments once per band
    French overseas prefixes once per band
    non-French DXCC countries once per band (available only to French stations)
    """
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text().upper()
    self.contact["NR"] = self.other_2.text().upper()

    self.contact["IsMultiplier1"] = 0
    self.contact["IsMultiplier2"] = 0

    if (
        self.contact.get("CountryPrefix", "") == "F"
        and self.contact.get("NR", "").isalpha()
    ):
        canton = self.contact.get("NR", "").upper()
        band = self.contact.get("Band", "")
        query = (
            f"select count(*) as canton_count from dxlog where "
            f"NR = '{canton}' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        count = int(result.get("canton_count", 0))
        if count == 0:
            self.contact["IsMultiplier1"] = 1

    if self.contact.get("CountryPrefix", ""):
        dxcc = self.contact.get("CountryPrefix", "")
        band = self.contact.get("Band", "")
        query = (
            f"select count(*) as dxcc_count from dxlog where "
            f"CountryPrefix = '{dxcc}' "
            f"and Band = '{band}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        if not result.get("dxcc_count", ""):
            self.contact["IsMultiplier2"] = 1


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    field = self.field3.findChild(QtWidgets.QLineEdit)
    sent_sxchange_setting = self.contest_settings.get("SentExchange", "")
    if sent_sxchange_setting.strip() == "#":
        result = self.database.get_serial()
        serial_nr = str(result.get("serial_nr", "1")).zfill(3)
        if serial_nr == "None":
            serial_nr = "001"
        if len(field.text()) == 0:
            field.setText(serial_nr)
    else:
        field.setText(sent_sxchange_setting)


def points(self):
    """
    Scoring:
    French: 6 points per QSO with French station same continent
    French: 15 points per QSO with French station on different continent
    French: 1 point per QSO with non-French station same continent
    French: 2 points per QSO with non-French station on different continent
    non-French: 1 point per QSO with French station same continent
    non-French: 3 points per QSO with French station on different continent

    self.contact["CountryPrefix"]
    self.contact["Continent"]
    """

    # Just incase the cty lookup fails
    my_country = None
    my_continent = None
    their_continent = None
    their_country = None

    result = self.cty_lookup(self.station.get("Call", ""))
    if result:
        for item in result.items():
            my_country = item[1].get("entity", "")
            my_continent = item[1].get("continent", "")
    result = self.cty_lookup(self.contact.get("Call", ""))
    if result:
        for item in result.items():
            their_country = item[1].get("entity", "")
            their_continent = item[1].get("continent", "")

    if my_country == "France":
        if their_country == "France":
            if my_continent == their_continent:
                return 6
            else:
                return 15
        else:
            if my_continent == their_continent:
                return 1
            else:
                return 2
    else:
        if their_country == "France":
            if their_continent == my_continent:
                return 1
            else:
                return 3

    return 0


def show_mults(self):
    """Return display string for mults"""
    return int(self.database.fetch_mult_count(1).get("count", 0)) + int(
        self.database.fetch_mult_count(2).get("count", 0)
    )


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


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""

    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:

        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = 0

        time_stamp = contact.get("TS", "")
        canton = contact.get("NR", "")
        dxcc = contact.get("CountryPrefix", "")
        band = contact.get("Band", "")
        if dxcc == "HB" and canton.isalpha():
            query = (
                f"select count(*) as canton_count from dxlog where  TS < '{time_stamp}' "
                f"and NR = '{canton.upper()}' "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            result = self.database.exec_sql(query)
            count = int(result.get("canton_count", 0))
            if count == 0:
                contact["IsMultiplier1"] = 1

        if dxcc:
            query = (
                f"select count(*) as dxcc_count from dxlog where TS < '{time_stamp}' "
                f"and CountryPrefix = '{dxcc}' "
                f"and Band = '{band}' "
                f"and ContestNR = {self.pref.get('contest', '1')};"
            )
            result = self.database.exec_sql(query)
            if not result.get("dxcc_count", ""):
                contact["IsMultiplier2"] = 1

        self.database.change_contact(contact)
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    cmd["station"] = platform.node()
    self.multicast_interface.send_as_json(cmd)


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "REF-SSB")


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
        with open(filename, "w", encoding="utf-8") as file_descriptor:
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
            output_cabrillo_line(
                f"CATEGORY-MODE: {self.contest_settings.get('ModeCategory','')}",
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
