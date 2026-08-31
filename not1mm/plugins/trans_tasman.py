"""TRANS TASMAN plugin"""

# Trans-Tasman Low-Band Contest
#   Status:    Active
#   Geographic Focus:    Australia (VK) and New Zealand (ZL)
#   Participation:    VK and ZL stations only
#   Awards:    Oceania
#   Mode:    SSB / CW / Digital (RTTY or PSK)
#   Bands:    160, 80 and 40m only
#   Classes:    Single Op HP/LP/QRP, Multi-One, Multi-Multi, YOUTH overlay
#   Exchange:    RS(T) + serial number (001 per band for multi-multi)
#   Work stations:    Once per band per mode in every 2-hour block
#                     (3 blocks from 0800 UTC)
#   QSO Points:    All valid VK/ZL contacts - 1 point
#   Multipliers:    Each different prefix used by VK or ZL stations, once per
#                   band per block
#   Score Calculation:    For each block: contacts in block x prefixes in
#                         block, summed over the 3 blocks
#   E-mail logs to:    ttlogs@wia.org.au
#   Upload log at:    https://www.vklogchecker.com/
#   Find rules at:    https://www.wia.org.au/members/contests/transtasman/
#   Cabrillo name:    WIA-TRANS TASMAN

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.ham_utility import calculate_wpx_prefix, get_logged_band
from not1mm.lib.plugin_common import gen_adif, get_points, imp_adif, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

assert QtWidgets
assert imp_adif
assert online_score_xml

EXCHANGE_HINT = "#"
SOAPBOX_HINT = "This has not been tested. Good Luck."

name = "Trans Tasman"
cabrillo_name = "WIA-TRANS TASMAN"
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
    "M1",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
# Rule: a station can be worked once per band per mode per 2-hour block.
dupe_type = 5

_PHONE_MODES = ("LSB", "USB", "SSB", "FM", "AM")

# Prefixes used by stations operating within Australia or New Zealand and
# their external territories (eg VK9, VK0, ZK, ZM). cty.json maps the entities
# but not all external territories to a VK/ZL primary_pfx, so match the WPX
# prefix instead. The contest counts e.g. VK9 once, not per island.
_VK_ZL_PREFIXES = ("VK", "ZL", "ZK", "ZM")


def _band_from_contact(contact: dict) -> str:
    """Return the canonical DXLOG band value (e.g. '7.0') for a contact."""
    band = str(contact.get("Band", ""))
    if not band or band == "0.0":
        freq = contact.get("Freq", 0)
        if freq:
            band = get_logged_band(str(float(freq) * 1_000_000))
    return str(float(band))


def _get_band(self) -> str:
    """Return the canonical DXLOG band value for the current contact."""
    return _band_from_contact(self.contact)


def _mode_group(mode: str) -> str:
    """Group a radio mode into PH, CW or DIGI per the contest rules.

    SSB, CW and Digital (RTTY/PSK) are the three allowed mode classes.
    """
    if mode in _PHONE_MODES:
        return "PH"
    if str(mode).startswith("CW"):
        return "CW"
    return "DIGI"


def _block_from_ts(ts: str) -> int:
    """Return the 2-hour block (0-2) for a UTC timestamp string.

    Blocks run 0800-1000, 1000-1200 and 1200-1400 UTC.
    """
    if len(ts) < 13:
        return 0
    hour = int(ts[11:13])
    if hour < 8:
        return 0
    if hour > 13:
        return 2
    return (hour - 8) // 2


def _block_boundaries(now: datetime.datetime) -> tuple:
    """Return the (start, end) UTC datetimes of the current 2-hour block."""
    if now.hour < 8:
        block = 0
    elif now.hour > 13:
        block = 2
    else:
        block = (now.hour - 8) // 2
    block_start = now.replace(hour=8 + 2 * block, minute=0, second=0, microsecond=0)
    block_end = block_start + datetime.timedelta(hours=2)
    return block_start, block_end


def _is_vk_zl_prefix(wpx: str) -> bool:
    """Return True if a WPX prefix belongs to a VK or ZL station.

    Covers mainland VK/ZL calls and their external territories (VK9, VK0, ZK,
    ZM). ZK and ZM are New Zealand prefixes that cty.json maps to ZL.
    """
    return wpx.startswith(_VK_ZL_PREFIXES)


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
    self.other_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "SentNR"))
    self.field3.setAccessibleName("Sent Number")
    self.exch_label.setText(QtWidgets.QApplication.translate("ContestPlugin", "RcvNR"))
    self.field4.setAccessibleName("Received Number")


def reset_label(self):  # pylint: disable=unused-argument
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


def set_contact_vars(self):
    """Contest Specific"""
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text()
    self.contact["NR"] = self.other_2.text()

    # stash the 2-hour block so dupes/mults can be checked per block.
    self.contact["MiscText"] = str(_block_from_ts(self.contact.get("TS", "")))

    band = _get_band(self)
    wpx = self.contact.get("WPXPrefix", "")
    if not wpx or not _is_vk_zl_prefix(wpx):
        self.contact["IsMultiplier1"] = 0
        return

    result = fetch_wpx_exists_before_me(self, wpx, band, self.contact.get("TS", ""))
    if result.get("wpx_count", ""):
        self.contact["IsMultiplier1"] = 0
    else:
        self.contact["IsMultiplier1"] = 1


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR with next serial number.

    Single Op runs the serial consecutively across all bands. Multi Op
    (multi-multi per the rules) restarts at 001 on each band.
    """
    operator_category = self.contest_settings.get("OperatorCategory", "")
    if operator_category == "SINGLE-OP":
        serial_nr = str(self.current_sn).zfill(3)
    else:
        result = self.database.exec_sql(
            "select max(SentNR) + 1 as serial_nr from DXLOG where ContestNR = ? and Band = ?;",
            (self.pref.get("contest", "1"), _get_band(self)),
        )
        serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)


def points(self):
    """All valid VK/ZL contacts are worth one point.

    Points are only awarded for contacts between two VK or ZL stations.
    """
    if self.contact_is_dupe > 0:
        return 0
    if not _is_vk_zl_prefix(self.contact.get("WPXPrefix", "")):
        return 0
    my_wpx = calculate_wpx_prefix(self.station.get("Call", ""))
    if not _is_vk_zl_prefix(my_wpx):
        return 0
    return 1


def _block_sql_expr() -> str:
    """SQL expression deriving the 2-hour block from a DXLOG TS value."""
    return (
        "CASE WHEN CAST(substr(TS,12,2) AS INTEGER) < 8 THEN 0 "
        "WHEN CAST(substr(TS,12,2) AS INTEGER) > 13 THEN 2 "
        "ELSE (CAST(substr(TS,12,2) AS INTEGER) - 8) / 2 END"
    )


def _vk_zl_wpx_filter(alias: str = "") -> str:
    """SQL WHERE fragment restricting a column to VK/ZL prefixes."""
    col = "WPXPrefix"
    if alias:
        col = f"{alias}.WPXPrefix"
    return (
        f"({col} like 'VK%' or {col} like 'ZL%' "
        f"or {col} like 'ZK%' or {col} like 'ZM%')"
    )


def show_mults(self):
    """Return display string for mults.

    Each different prefix used by VK or ZL stations counts once per band per
    block.
    """
    contest_nr = self.pref.get("contest", "0")
    query = f"""
        select count(DISTINCT(
            WPXPrefix || ':' || Band || ':' || {_block_sql_expr()}
        )) as mults
        from DXLOG
        where ContestNR = {contest_nr}
        and {_vk_zl_wpx_filter()};
        """
    result = self.database.exec_sql(query)
    if result:
        return int(result.get("mults", 0))
    return 0


def show_qso(self):
    """Return qso count (only VK/ZL contacts score in this contest)."""
    contest_nr = self.pref.get("contest", "0")
    query = f"""
        select count(*) as qsos
        from DXLOG
        where ContestNR = {contest_nr}
        and {_vk_zl_wpx_filter()};
        """
    result = self.database.exec_sql(query)
    if result:
        return int(result.get("qsos", 0))
    return 0


def calc_score(self):
    """Return calculated score.

    For each of the three 2-hour blocks: contacts in that block multiplied by
    the number of different prefixes worked on each band in that block. The
    final score is the sum of the three block scores.
    """
    contacts = self.database.fetch_all_contacts_asc()
    qso_count = {}
    mult_count = {}
    for contact in contacts:
        wpx = contact.get("WPXPrefix", "")
        if not _is_vk_zl_prefix(wpx):
            continue
        block = _block_from_ts(contact.get("TS", ""))
        qso_count[block] = qso_count.get(block, 0) + 1
        mult_count.setdefault(block, set()).add((contact.get("Band", ""), wpx))
    score = 0
    for block in (0, 1, 2):
        score += qso_count.get(block, 0) * len(mult_count.get(block, ()))
    return score


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "WIA-TRANS TASMAN")


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """Outputs a single line of cabrillo file in the proper encoding."""
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
                if themode in _PHONE_MODES:
                    themode = "PH"
                elif themode.startswith("CW"):
                    themode = "CW"
                elif themode.startswith("RTTY"):
                    themode = "RTTY"
                elif themode.startswith("PSK"):
                    themode = "PSK"
                else:
                    themode = "PH"
                frequency = str(round(float(contact.get("Freq", "0")) * 1000))

                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                output_cabrillo_line(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SNT', '')).ljust(3)} "
                    f"{str(contact.get('SentNr', '0')).rjust(3, '0').ljust(6)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('RCV', '')).ljust(3)} "
                    f"{str(contact.get('NR', '0')).rjust(3, '0').ljust(6)}",
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


def recalculate_mults(self):
    """Recalculates multipliers after change in logged qso."""
    self.contact_is_dupe = 0
    all_contacts = self.database.fetch_all_contacts_asc()
    for contact in all_contacts:
        self.contact = contact
        contact["Points"] = points(self)
        wpx = contact.get("WPXPrefix", "")
        band = str(contact.get("Band", ""))
        time_stamp = contact.get("TS", "")
        contact["MiscText"] = str(_block_from_ts(time_stamp))

        result = fetch_wpx_exists_before_me(self, wpx, band, time_stamp)
        if wpx and _is_vk_zl_prefix(wpx) and result.get("wpx_count", 1) == 0:
            contact["IsMultiplier1"] = 1
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)


def fetch_wpx_exists_before_me(self, wpx, band, time_stamp) -> dict:
    """returns a dict key of wpx_count for specific band and block."""
    contest_nr = self.pref.get("contest")
    block = _block_from_ts(time_stamp)

    query = """
        select count(*) as wpx_count from dxlog where
        TS < ?
        and WPXPrefix = ?
        and ContestNR = ?
        and Band = ?
        and CASE WHEN CAST(substr(TS,12,2) AS INTEGER) < 8 THEN 0
                 WHEN CAST(substr(TS,12,2) AS INTEGER) > 13 THEN 2
                 ELSE (CAST(substr(TS,12,2) AS INTEGER) - 8) / 2 END = ?
        ;"""

    result = self.database.exec_sql(
        query,
        (time_stamp, wpx, contest_nr, band, block),
    )
    return result


def specific_contest_check_dupe(self, call):
    """Return dict with isdupe True if the call was worked on this band and
    mode-group in the current 2-hour block."""
    mode = self.radio_state.get("mode", "")
    mode_group = _mode_group(mode)

    band = self.contact.get("Band", "")
    now = datetime.datetime.now(datetime.UTC)
    block_start, block_end = _block_boundaries(now)

    query = """
        select count(*) as isdupe from dxlog where
        Call = ?
        and Band = ?
        and ContestNR = ?
        and TS >= ?
        and TS < ?
        and CASE WHEN Mode IN ('LSB','USB','SSB','FM','AM') THEN 'PH'
                 WHEN Mode like 'CW%' THEN 'CW'
                 ELSE 'DIGI' END = ?
        ;"""

    result = self.database.exec_sql(
        query,
        (
            call,
            band,
            self.pref.get("contest", "0"),
            block_start.strftime("%Y-%m-%d %H:%M:%S"),
            block_end.strftime("%Y-%m-%d %H:%M:%S"),
            mode_group,
        ),
    )
    if result:
        return result
    return {"isdupe": False}


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


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["wpxprefix"] = show_mults(self)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
