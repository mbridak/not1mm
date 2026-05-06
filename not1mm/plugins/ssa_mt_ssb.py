"""SSA Manadstest SSB plugin"""

# SSA Manadstest - Swedish monthly HF contest, SSB mode.
#   Exchange:   RST + serial number + 6-character Maidenhead locator
#   Example:    59 01 JP75XX
#   Multipliers: unique 4-character locator prefixes per band
#   Score:      total QSO points * total multipliers
#   QSO points: 2 per valid QSO

import datetime
import logging

from pathlib import Path
from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

VALID_LOCATORS = {
    "JO57",
    "JO58",
    "JO59",
    "JO65",
    "JO66",
    "JO67",
    "JO68",
    "JO69",
    "JO75",
    "JO76",
    "JO77",
    "JO78",
    "JO79",
    "JO86",
    "JO87",
    "JO88",
    "JO89",
    "JO96",
    "JO97",
    "JO98",
    "JO99",
    "JP53",
    "JP60",
    "JP61",
    "JP62",
    "JP63",
    "JP64",
    "JP70",
    "JP71",
    "JP72",
    "JP73",
    "JP74",
    "JP75",
    "JP76",
    "JP80",
    "JP81",
    "JP82",
    "JP83",
    "JP84",
    "JP85",
    "JP86",
    "JP87",
    "JP88",
    "JP90",
    "JP92",
    "JP93",
    "JP94",
    "JP95",
    "JP96",
    "JP97",
    "JP98",
    "KP03",
    "KP04",
    "KP05",
    "KP06",
    "KP07",
    "KP08",
    "KP09",
    "KP15",
    "KP16",
    "KP17",
    "KP18",
    "KP25",
    "KP26",
}

EXCHANGE_HINT = "# LocXXXX"

name = "SSA MT SSB"
cabrillo_name = "SSA-MT-SSB"
mode = "SSB"
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq (KHz)",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
    "Exchange1",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 once per band, 3 once per band/mode, 4 no dupe checking
dupe_type = 2


def init_contest(self):
    """Setup plugin"""
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2
    self._exch_sent = False


def interface(self):
    """Setup user interface"""
    self.field1.show()
    self.field2.show()
    self.field3.show()
    self.field4.show()
    self.sent.setReadOnly(False)
    self.snt_label.setText("Sent")
    self.rcv_label.setText("Received")
    self.field1.setAccessibleName("Signal report Sent")
    self.other_label.setText("Nr")
    self.field3.setAccessibleName("Received Serial Number")
    self.exch_label.setText("Locator")
    self.field4.setAccessibleName("Received Locator")


def reset_label(self):
    """Reset label after field cleared"""


def set_tab_next(self):
    """Set TAB advance order"""
    self.tab_next = {
        self.callsign: self.sent,
        self.sent: self.receive,
        self.receive: self.other_1,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set reverse TAB order"""
    self.tab_prev = {
        self.callsign: self.other_2,
        self.sent: self.callsign,
        self.receive: self.sent,
        self.other_1: self.receive,
        self.other_2: self.other_1,
    }


def set_contact_vars(self):
    """Map UI fields to contact record"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text() or "59"
    self.contact["SentNr"] = self.current_sn
    self.contact["GridSquare"] = self.contest_settings.get("SentExchange", "")
    self.contact["NR"] = self.other_1.text()
    self.contact["Exchange1"] = self.other_2.text().upper()


def predupe(self):
    """Pre-fill locator from call history on each callsign keystroke"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        name = result.get("Name", "") or ""
        loc = result.get("Loc1", "") or ""
        info = ", ".join(x for x in [result.get("Call", ""), name, loc] if x)
        self.history_info.setText(info)
        self.other_2.setText(loc)
    else:
        self.other_2.setText("")
        self.history_info.setText("")


def prefill(self):
    """Pre-fill sent RST"""
    if len(self.sent.text()) == 0:
        self.sent.setText("59")


def points(self):
    """Return QSO point value"""
    if self.contact_is_dupe > 0:
        return 0
    return 2


def show_mults(self):
    """Return multiplier count: distinct 4-char locator prefixes per band"""
    sql = (
        "select count(DISTINCT(SUBSTR(Exchange1, 1, 4) || ':' || Band)) as mult_count "
        f"from dxlog where ContestNR = {self.database.current_contest} "
        "and typeof(Exchange1) = 'text' "
        "and LENGTH(Exchange1) >= 4;"
    )
    result = self.database.exec_sql(sql)
    if result:
        return int(result.get("mult_count", 0))
    return 0


def show_qso(self):
    """Return QSO count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score"""
    _points = get_points(self)
    _mults = show_mults(self)
    return _points * _mults


def adif(self):
    """Generate ADIF export"""
    gen_adif(self, cabrillo_name)


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Write one encoded line to the Cabrillo file"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo(self, file_encoding):
    """Generate Cabrillo log file"""
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now()
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
                "START-OF-LOG: 3.0", "\r\n", file_descriptor, file_encoding
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
            output_cabrillo_line(
                f"CATEGORY-MODE: {self.contest_settings.get('ModeCategory', '')}",
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
                f"OPERATORS: {ops}", "\r\n", file_descriptor, file_encoding
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
                f"ADDRESS: {self.station.get('City', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS: {self.station.get('Zip', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS: {self.station.get('Country', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            output_cabrillo_line(
                f"ADDRESS: {self.station.get('Email', '')}",
                "\r\n",
                file_descriptor,
                file_encoding,
            )
            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = contact.get("Mode", "")
                if themode in ("CW-U", "CW-L", "CW-R", "CWR"):
                    themode = "CW"
                if themode in ("LSB", "USB", "AM"):
                    themode = "PH"
                if themode in (
                    "FT8",
                    "FT4",
                    "RTTY",
                    "PSK31",
                    "FSK441",
                    "MSK144",
                    "JT65",
                    "JT9",
                    "Q65",
                ):
                    themode = "DG"
                frequency = str(round(contact.get("Freq", 0))).rjust(5)
                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                sent_nr = str(contact.get("SentNr", "0")).zfill(3)
                rcv_nr = str(contact.get("NR", "0")).zfill(3)
                sent_loc = contact.get("GridSquare", "")
                rcv_loc = contact.get("Exchange1", "")
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{sent_nr} "
                    f"{sent_loc.ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{rcv_nr} "
                    f"{rcv_loc}",
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
    """Walk all contacts and flag the first occurrence of each locator-prefix+Band as a mult"""
    all_contacts = self.database.fetch_all_contacts_asc()
    seen = set()
    for contact in all_contacts:
        exch = contact.get("Exchange1", "")
        band = contact.get("Band", "")
        if len(exch) >= 4:
            key = exch[:4].upper() + ":" + band
            if key not in seen:
                seen.add(key)
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)


def _validate_field(widget, valid):
    """Color widget red if invalid, reset otherwise"""
    if valid:
        widget.setStyleSheet("")
    else:
        widget.setStyleSheet("background-color: #5c0000;")


def _check_rst(value, rst_min=11, rst_max=59):
    """Return True if value is a valid RST in range"""
    try:
        v = int(value)
        return rst_min <= v <= rst_max
    except ValueError:
        return False


def _check_nr(value):
    """Return True if value is a valid serial number"""
    try:
        v = int(value)
        return 1 <= v <= 999
    except ValueError:
        return False


def _check_locator(value):
    """Return True if value is a valid 6-char Swedish contest locator"""
    if len(value) != 6:
        return False
    prefix = value[:4].upper()
    suffix = value[4:].upper()
    return prefix in VALID_LOCATORS and suffix.isalpha()


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

    if self.current_widget == "callsign":
        self._exch_sent = False

    _validate_field(self.sent, not self.sent.text() or _check_rst(self.sent.text()))
    _validate_field(
        self.receive, not self.receive.text() or _check_rst(self.receive.text())
    )
    _validate_field(
        self.other_1, not self.other_1.text() or _check_nr(self.other_1.text())
    )
    _validate_field(
        self.other_2, not self.other_2.text() or _check_locator(self.other_2.text())
    )

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
            elif self.contact_is_dupe:
                self.make_button_green(self.esm_dict["QSOB4"])
                buttons_to_send.append(self.esm_dict["QSOB4"])
            elif len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["HISCALL"])
                buttons_to_send.append(self.esm_dict["EXCH"])

        elif self.current_widget == "other_1":
            if self.other_1.text() == "":
                self.make_button_green(self.F11)
                buttons_to_send.append(self.F11)
            else:
                if with_enter is True:
                    self.other_2.setFocus()
                    return

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.F12)
                buttons_to_send.append(self.F12)
            else:
                self.make_button_green(self.esm_dict["QRZ"])
                buttons_to_send.append(self.esm_dict["QRZ"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        if (
                            not _check_rst(self.sent.text())
                            or not _check_rst(self.receive.text())
                            or not _check_nr(self.other_1.text())
                            or not _check_locator(self.other_2.text())
                        ):
                            return
                        self.save_contact()
                        continue
                    self.process_function_key(button)
            if self.contact_is_dupe:
                return
            if self.current_widget == "callsign" and len(self.callsign.text()) > 2:
                self.other_1.setFocus()
    else:
        if self.current_widget == "callsign":
            if self.contact_is_dupe:
                self.make_button_green(self.esm_dict["QSOB4"])
                buttons_to_send.append(self.esm_dict["QSOB4"])
            elif len(self.callsign.text()) > 2:
                self.make_button_green(self.esm_dict["MYCALL"])
                buttons_to_send.append(self.esm_dict["MYCALL"])

        elif self.current_widget == "other_1":
            if self.other_1.text() == "":
                self.make_button_green(self.F11)
                buttons_to_send.append(self.F11)
            else:
                if with_enter is True:
                    self.other_2.setFocus()
                    return

        elif self.current_widget == "other_2":
            if self.other_2.text() == "":
                self.make_button_green(self.F12)
                buttons_to_send.append(self.F12)
            elif not self._exch_sent:
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["EXCH"])
                if with_enter is True:
                    self._exch_sent = True
            else:
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append("LOGIT")

        if with_enter is True and bool(len(buttons_to_send)):
            for button in buttons_to_send:
                if button:
                    if button == "LOGIT":
                        if (
                            not _check_rst(self.sent.text())
                            or not _check_rst(self.receive.text())
                            or not _check_nr(self.other_1.text())
                            or not _check_locator(self.other_2.text())
                        ):
                            return
                        self.save_contact()
                        continue
                    self.process_function_key(button)
            if self.current_widget == "callsign":
                self.other_1.setFocus()


def populate_history_info_line(self):
    """Fill history info label from call history"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        name = result.get("Name", "") or ""
        loc = result.get("Loc1", "") or ""
        usertext = result.get("UserText", "") or ""
        info = ", ".join(x for x in [result.get("Call", ""), name, loc, usertext] if x)
        self.history_info.setText(info)
    else:
        self.history_info.setText("")


def check_call_history(self):
    """Pre-fill locator from call history if available"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText', '')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Loc1', '')}")


def get_mults(self):
    """Return mult dict for RTC XML"""
    mults = {}
    mults["locator"] = show_mults(self)
    return mults


def just_points(self):
    """Return raw points for RTC XML"""
    return get_points(self)


def imp_adif(self):
    """Import ADIF log"""
    imp_adif(self)
