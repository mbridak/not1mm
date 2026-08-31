"""California QSO Party plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import

#   California QSO Party
#   Status: Active
#   Geographic Focus: US
#   Participation: Worldwide
#   Mode: CW, Phone
#   Bands: 160, 80, 40, 20, 15, 10 meters
#   Classes: Single-Op (QRP/Low/High), Single-Op-Assisted (QRP/Low/High),
#            Multi-Single (QRP/Low/High), Multi-Two (QRP/Low/High),
#            Multi-Multi (QRP/Low/High), Checklog
#   Max operating hours: 24 (SO/SOA), 30 (Multi)
#   Max power: HP: >100 watts, LP: <=100 watts, QRP: <=5 watts
#   Exchange: Serial No. + 4-letter county abbreviation (CA stations)
#             Serial No. + 2-letter state/province/DX (non-CA stations)
#   Work stations: Once per band per mode (max 12 QSOs per station)
#   QSO Points: 3 points per QSO (Phone and CW)
#   Multipliers:
#     CA stations: US states + Canadian provinces/territories (max 58)
#     Non-CA stations: 58 California counties (max 58)
#     DX does not count as a multiplier for CA stations
#   Score Calculation: Total QSO points x total multipliers
#   Cabrillo name: CQP
#   Cabrillo QSO format:
#     QSO: freq  mo date       time call          sent_nr sent_qth call          recv_nr recv_qth

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

ALTEREGO = None
EXCHANGE_HINT = "State/Province (non-CA) or County (CA)"
SOAPBOX_HINT = "California QSO Party - Exchange: serial + state/county abbreviation"

name = "California QSO Party"
mode = "BOTH"  # CW SSB BOTH RTTY
cabrillo_name = "CQP"

# California 4-letter county abbreviations (58 total)
# Used to validate CA station exchanges and for mult checking
CA_COUNTIES = {
    "ALAM",
    "ALPI",
    "AMAD",
    "BUTT",
    "CALA",
    "CCOS",
    "COLU",
    "DELN",
    "ELDO",
    "FRES",
    "GLEN",
    "HUMB",
    "IMPE",
    "INYO",
    "KERN",
    "KING",
    "LAKE",
    "LASS",
    "LANG",
    "MADE",
    "MARN",
    "MARP",
    "MEND",
    "MERC",
    "MODO",
    "MONO",
    "MONT",
    "NAPA",
    "NEVA",
    "ORAN",
    "PLAC",
    "PLUM",
    "RIVE",
    "SACR",
    "SBAR",
    "SBEN",
    "SBER",
    "SCLA",
    "SCRU",
    "SDIE",
    "SFRA",
    "SHAS",
    "SJOA",
    "SIER",
    "SISK",
    "SLUI",
    "SOLA",
    "SONO",
    "STAN",
    "SUTT",
    "SMAT",
    "TEHA",
    "TRIN",
    "TULA",
    "TUOL",
    "VENT",
    "YOLO",
    "YUBA",
}

# US state/province 2-letter abbreviations (63 total: 50 states + 13 Canadian)
# Used for CA station multipliers. DX does not count as a mult for CA stations.
CA_MULTS = {
    # US states
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
    # Canadian provinces/territories
    "AB",
    "BC",
    "MB",
    "NB",
    "NL",
    "NT",
    "NS",
    "NU",
    "ON",
    "PE",
    "QC",
    "SK",
    "YT",
}

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Mode",
    "SentNr",
    "RcvNr",
    "Exchange1",
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
    self.next_field = self.other_1


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.hide()
    self.snt_label.setText("SentNR")
    self.sent.setAccessibleName("SentNR")
    self.rcv_label.setText("RcvNR")
    self.receive.setAccessibleName("RcvNR")
    self.other_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "State/County")
    )
    self.other_1.setAccessibleName("State/County")


def reset_label(self):
    """reset label after field cleared"""


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.callsign,
    }


def set_tab_prev(self):
    """Set Shift-TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_1,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
    }


def is_valid_ca_county(text: str) -> bool:
    """Return True if text is a valid 4-letter California county abbreviation."""

    return text.upper().strip() in CA_COUNTIES


def is_valid_state_province(text: str) -> bool:
    """Return True if text is a valid 2-letter US state or Canadian province abbreviation."""

    return text.upper().strip() in CA_MULTS


def is_valid_exchange(text: str) -> bool:
    """Return True if text is a valid exchange (county or state/province)."""

    upper = text.upper().strip()
    return upper in CA_COUNTIES or upper in CA_MULTS or upper == "DX"


def normalize_exchange(text: str) -> str:
    """Return the normalized (uppercased, stripped) exchange text."""

    return text.upper().strip()


def points_for_qso(mode: str, is_dupe: bool) -> int:
    """Return QSO points. 3 points for both Phone and CW. 0 for dupes."""

    if is_dupe:
        return 0
    return 3


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SentNr"] = self.sent.text()
    self.contact["NR"] = self.receive.text()
    self.contact["Exchange1"] = normalize_exchange(self.other_1.text())

    self.contact["IsMultiplier1"] = 0
    self.contact["IsMultiplier2"] = 0

    exch = self.contact.get("Exchange1", "").upper()
    if exch and exch != "DX":
        query = (
            f"select count(*) as exch_count from dxlog where "
            f"Exchange1 = '{exch}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        count = int(result.get("exch_count", 0))
        if count == 0:
            self.contact["IsMultiplier1"] = 1


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    # serial_nr = str(self.current_sn).zfill(3)
    # if serial_nr == "None":
    #     serial_nr = "001"
    # if len(self.sent.text()) == 0:
    #     self.sent.setText(serial_nr)

    # exchange = self.contest_settings.get("SentExchange", "").upper()
    # if len(self.other_1.text()) == 0 and exchange:
    #     self.other_1.setText(exchange)


def points(self):
    """Calc point - 3 points per QSO for both Phone and CW"""

    return points_for_qso(self.contact.get("Mode", ""), self.contact_is_dupe > 0)


def show_mults(self):
    """Return display string for mults"""
    # CA stations: states/provinces (capped at 58)
    # Non-CA stations: CA counties (capped at 58)
    # The 58 cap is natural since those are the max possible distinct values

    dx = 0
    sql = (
        "select count(DISTINCT Exchange1) as mult_count "
        "from dxlog where "
        f"ContestNR = {self.database.current_contest} "
        "and typeof(Exchange1) = 'text' "
        "and Exchange1 != 'DX';"
    )
    result = self.database.exec_sql(sql)

    if result:
        dx = result.get("mult_count", 0)

    return min(dx, 58)


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    # Total score = total QSO points x total multipliers (max 58)
    _points = get_points(self)
    _mults = show_mults(self)
    return _points * _mults


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""

    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        contact["IsMultiplier1"] = 0

        time_stamp = contact.get("TS", "")
        exch = contact.get("Exchange1", "")
        query = (
            f"select count(*) as exch_count from dxlog where TS < '{time_stamp}' "
            f"and Exchange1 = '{exch.upper()}' "
            f"and ContestNR = {self.pref.get('contest', '1')};"
        )
        result = self.database.exec_sql(query)
        count = int(result.get("exch_count", 0))
        if count == 0:
            contact["IsMultiplier1"] = 1

        self.database.change_contact(contact)

    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if self.log_window:
        self.log_window.msg_from_main(cmd)


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "QSO_PARTY")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generates Cabrillo file."""
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now().astimezone()
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

                match themode:
                    case "LSB" | "USB" | "SSB" | "FM" | "AM":
                        themode = "PH"
                    case "CW" | "CW-U" | "CW-L" | "CWR" | "CW-R":
                        themode = "CW"

                freq = contact.get("Freq", "0") / 1000

                frequency = str(round(freq)).rjust(5)

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]

                sent_nr = str(contact.get("SentNr", "")).strip()
                sent_qth = str(contact.get("Exchange1", "")).upper().strip()

                recv_nr = str(contact.get("NR", "")).strip()

                # In Cabrillo: our sent QTH goes in sent position,
                # their received QTH goes in received position.
                # The Cabrillo format is:
                # QSO: freq mo date time my_call sent_nr sent_qth their_call recv_nr recv_qth
                my_qth = self.contest_settings.get("SentExchange", "").upper()

                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{sent_nr.ljust(6)} "
                    f"{my_qth.ljust(5)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{recv_nr.ljust(6)} "
                    f"{sent_qth.ljust(5)}",
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


def populate_history_info_line(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Exch1', '')}"
        )
    else:
        self.history_info.setText("")


def check_call_history(self):
    result = self.database.fetch_call_history(self.callsign.text())
    if result and self.other_1.text() == "":
        self.other_1.setText(f"{result.get('Exch1', '')}")


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

        elif self.current_widget == "other_1":
            if self.other_1.text() == "":
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

        elif self.current_widget == "other_1":
            if self.other_1.text() == "":
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
