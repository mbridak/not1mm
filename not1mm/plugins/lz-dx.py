"""
@dg9vh
LZ-DX
-------------------------------------------------
Status:	Active
Geographic Focus:	Bulgaria
Participation:	Worldwide
Mode:	CW, SSB
Bands:	80, 40, 20, 15, 10m
Classes:	Single Op (CW/SSB) High
            Single Op Mixed (QRP/Low/High)
            Multi-Op (CW/SSB/Mixed) High
            SWL
Max operating hours:	18 with a maximum of two rest periods of any length
Max power:	HP: >100 watts
LP: 100 watts
QRP: 5 watts (CW/Digital) or 10 watts (SSB)
Exchange:	LZ: RS(T) + 2-letter district
            non-LZ: RS(T) + ITU zone
Work stations:	Once on CW and once on SSB on each band

Scoring:
Contact with a station in Bulgaria: 10 points
Contact with a station within the same continent: 1 point
Contact with a station outside the operator's continent: 3 points
Contact between two LZ stations: 1 point

Multipliers: per band and regardless of mode - ITU zones for every entrant,
plus LZ districts for a foreign entrant or DXCC countries for an LZ one

Score Calculation:	Total score = total QSO points x total mults
Mail logs to:	lzdxc@bfra.bg
Find rules at:	https://lzdx.bfra.bg/rulesen.html
Cabrillo name:	LZ-DX
"""

import datetime
import logging
from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, get_points, imp_adif, online_score_xml
from not1mm.lib.version import __version__

assert online_score_xml
assert imp_adif

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "District or ITU-Zone"

name = "LZ DX"
cabrillo_name = "LZ-DX"
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
    "M2",
    "PTS",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 3

cantons = [
    "BU",
    "BL",
    "VN",
    "VD",
    "VR",
    "GA",
    "DO",
    "KA",
    "KD",
    "LV",
    "MN",
    "PA",
    "PK",
    "PL",
    "PD",
    "RZ",
    "RS",
    "SS",
    "SL",
    "SM",
    "SF",
    "SO",
    "SZ",
    "TA",
    "HA",
    "SN",
    "YA",
]


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
        QtWidgets.QApplication.translate("ContestPlugin", "District/ITU")
    )
    self.other_2.setAccessibleName("District or ITU")


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

    if (
        self.contact.get("CountryPrefix", "") == "LZ"
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
    """Return display string for mults.

    Per band and regardless of mode: ITU zones for every entrant, plus the LZ
    districts for a foreign entrant or the DXCC countries for an LZ one.  The
    old code counted districts and countries for everyone and never counted
    zones at all.
    """
    contest = self.pref.get("contest", "1")
    result = self.database.exec_sql(
        "select count(DISTINCT ZN || ':' || Band) as zone_count from dxlog "
        f"where ContestNR = {contest} and ZN > 0;"
    )
    zones = int(result.get("zone_count", 0) or 0) if result else 0

    if _is_lz(self):
        result = self.database.exec_sql(
            "select count(DISTINCT CountryPrefix || ':' || Band) as other_count "
            f"from dxlog where ContestNR = {contest} and CountryPrefix != '';"
        )
    else:
        result = self.database.exec_sql(
            "select count(DISTINCT NR || ':' || Band) as other_count from dxlog "
            f"where ContestNR = {contest} and CountryPrefix = 'LZ' "
            "and typeof(NR) = 'text' and NR != '';"
        )
    others = int(result.get("other_count", 0) or 0) if result else 0
    return zones + others


def show_qso(self):
    """Return qso count"""
    result = self.database.fetch_qso_count()
    if result:
        return int(result.get("qsos", 0))
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "LZ-DX")


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
    except OSError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def check_call_history(self):
    """"""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText', '')}")
        if self.other_2.text() == "":
            self.other_2.setText(f"{result.get('Exch1', '')}")


def predupe(self):
    """called after callsign entered"""


def _entity(self, call):
    """Return ``(entity, continent)`` for a callsign, or ``("", "")``."""
    result = self.cty_lookup(call)
    if not result:
        return "", ""
    item = result.get(next(iter(result)), {})
    return item.get("entity", ""), item.get("continent", "")


def _is_lz(self) -> bool:
    """True when the entrant is a Bulgarian station."""
    return _entity(self, self.station.get("Call", ""))[0] == "Bulgaria"


def points(self):
    """
    Scoring:
    Contact with a station in Bulgaria: 10 points
    Contact with a station within the same continent: 1 point
    Contact with a station outside the operator's continent: 3 points
    Contact between two LZ stations: 1 point
    """
    if self.contact_is_dupe > 0:
        return 0

    their_country, their_continent = _entity(self, self.contact.get("Call", ""))
    if not their_country:
        return 0

    # The entrant's own lookup can fail too; _entity guards that now, where
    # before my_continent was left unbound and points() raised.
    my_country, my_continent = _entity(self, self.station.get("Call", ""))

    if my_country == "Bulgaria" and their_country == "Bulgaria":
        return 1
    if their_country == "Bulgaria":
        return 10
    if my_continent != their_continent:
        return 3
    return 1


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

    # IsMultiplier1 marks a new ITU zone per band and IsMultiplier2 a new
    # district (foreign entrant) or DXCC country (LZ entrant) per band, which
    # is what show_mults() counts.
    im_lz = _is_lz(self)
    seen_zones = set()
    seen_other = set()
    for contact in self.database.fetch_all_contacts_asc():
        contact["IsMultiplier1"] = 0
        contact["IsMultiplier2"] = 0

        band = str(contact.get("Band", ""))
        zone = contact.get("ZN", 0)
        if zone:
            key = (str(zone), band)
            if key not in seen_zones:
                seen_zones.add(key)
                contact["IsMultiplier1"] = 1

        if im_lz:
            dxcc = contact.get("CountryPrefix", "")
            key = (dxcc, band)
            if dxcc and key not in seen_other:
                seen_other.add(key)
                contact["IsMultiplier2"] = 1
        elif contact.get("CountryPrefix", "") == "LZ" and str(
            contact.get("NR", "")
        ).isalpha():
            key = (str(contact.get("NR", "")).upper(), band)
            if key not in seen_other:
                seen_other.add(key)
                contact["IsMultiplier2"] = 1

        self.database.change_contact(contact)
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if self.log_window:
        self.log_window.msg_from_main(cmd)


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
