"""RSGB 80M CC plugin"""

# pylint: disable=invalid-name, c-extension-no-member, unused-import

# RSGB 3.5MHz Club Championship Contests
#
# The RSGB 3.5MHz Autumn Series (Cabrillo RSGB-80M-AUT) is a similar series
# sharing this Cabrillo format and these per-QSO rules, but it adds a
# licence-class multiplier for club scores and a "Le Mans" start penalty, and
# it is not covered by this plugin.
#  	Status:	Active
#  	Geographic Focus:	UK and Crown dependencies
#  	Participation:	Worldwide
#  	Awards:	Worldwide
#  	Modes:	CW, SSB, RTTY/PSK
#  	Bands:	80m
#  	Classes:	Single Op (Low - 10W/High - 100W )  (Assisted/Non-assisted)
#   100W/10W Assisted and 100W/10W Unassisted Sections
#  	Max operating hours:	Single Op and Multi-Op: 90 minutes per session
#  	Max power:	LP: 10 watts; HP: 100 watts
#  	Exchange:	RST + Serial No.
#  	Work stations:	Once per mode (PSK63 and RTTY are separate modes)
#  	QSO Points:	1 per QSO, 5 for a QSO with the RSGB station (G6XX or a regional variant)
#  	Multipliers:	None
#  	Score Calculation:	Total score = total QSO points
#  	E-mail logs to:	(none)
#  	Upload log at:	http://www.rsgbcc.org/cgi-bin/hfenter.pl
#  	Mail logs to:	(none)
#  	Find rules at:	https://www.rsgbcc.org/hf/rules/2026/r80mcc.shtml
#  	Cabrillo name:	RSGB-80M-CC

import datetime
import logging
import re

from pathlib import Path

from PyQt6 import QtWidgets

from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "#"

name = "RSGB 80M CC"
cabrillo_name = "RSGB-80M-CC"
mode = "CW"  # CW SSB BOTH RTTY
# columns = [0, 1, 2, 3, 4, 5, 6, 9, 11, 15]
columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "Snt",
    "Rcv",
    "SentNr",
    "RcvNr",
]

advance_on_space = [True, True, True, True, True]

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
# 5 custom: the sessions are single-band, and the DATA ones count PSK63 and
# RTTY as different modes, so "once per session" is once per mode with those
# two kept apart.
dupe_type = 5

# Rule 6: a UK&CD station is required at one or both ends of a contact for it
# to count for points.  CD is the Crown Dependencies; the Republic of Ireland
# is a separate country and is not part of UK&CD.
UKCD_ENTITIES = (
    "England",
    "Scotland",
    "Wales",
    "Northern Ireland",
    "Guernsey",
    "Jersey",
    "Isle of Man",
)


def _is_ukcd(self, call) -> bool:
    """Return True if `call` is in the UK, the Crown Dependencies or NI."""
    result = self.cty_lookup(call)
    if result is not None:
        item = result.get(next(iter(result)))
        return item.get("entity", "") in UKCD_ENTITIES
    return False


# The Society's station is G6XX and its regional variants.  The regional
# secondary locator follows either G or M - Wales is GW6XX or MW6XX, Scotland
# is GM6XX or MM6XX - so both spellings have to be recognised.  A bare M6XX is
# deliberately not matched: that is an ordinary English full-licence call.
RSGB_STATION_RE = re.compile(r"^(?:G|G[DEIJMUW]|M[DEIJMUW])6XX$")


def is_rsgb_station(call: str) -> bool:
    """Rule 6: the Society's station, G6XX or a regional variant, scores 5."""
    return bool(RSGB_STATION_RE.match(str(call).upper().split("/")[0]))


def _dupe_mode(mode: str) -> str:
    """Group a mode for dupe checking.

    Phone modes are one group and the CW variants another, so a station worked
    on LSB and again on USB is still a dupe.  RTTY and the PSK family stay
    apart from each other, because rule 6 lets a station be worked "once on
    PSK63 and once on RTTY".
    """
    upper = str(mode).upper()
    if upper.startswith("PSK") or upper.startswith("BPSK"):
        return "PSK"
    if upper.startswith("RTTY") or upper in ("FSK", "RY"):
        return "RTTY"
    if upper in ("LSB", "USB", "SSB", "FM", "AM", "PH"):
        return "PH"
    if upper.startswith("CW"):
        return "CW"
    return upper


# Rule 7: "check that you have used the correct Cabrillo Mode Codes: RTTY =
# RY, PSK63 = PS, PK or PM, SSB = PH, CW = CW".  A rig reports PSK31 rather
# than PSK63, so the PSK family has to be matched as a group.
CABRILLO_MODE = {"CW": "CW", "PH": "PH", "RTTY": "RY", "PSK": "PS"}


def _cabrillo_mode(mode: str) -> str:
    """Return the Cabrillo mode code for `mode`."""
    return CABRILLO_MODE.get(_dupe_mode(mode), mode)


def specific_contest_check_dupe(self, call):
    """Rule 6: a station may be worked once per mode in this session.

    The sessions are single-band, so "once per session" is once per mode.  A
    duplicate still has to be logged - it just scores nothing.
    """
    state = getattr(self, "radio_state", None) or {}
    want = _dupe_mode(state.get("mode") or self.contact.get("Mode", ""))
    for contact in self.database.fetch_all_contacts_asc():
        if str(contact.get("Call", "")).upper() != str(call).upper():
            continue
        if _dupe_mode(contact.get("Mode", "")) == want:
            return {"isdupe": True}
    return {"isdupe": False}


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
    self.other_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "SentNR")
    )
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


def predupe(self):  # pylint: disable=unused-argument
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    # result = self.database.get_serial()
    # serial_nr = str(result.get("serial_nr", "1")).zfill(3)
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr == "None":
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)


def points(self):
    """Calc point"""

    if self.contact_is_dupe > 0:
        return 0

    # Rule 6: a UK&CD station must be at one or both ends of the contact.
    if not (
        _is_ukcd(self, self.station.get("Call", ""))
        or _is_ukcd(self, self.contact.get("Call", ""))
    ):
        return 0

    # Rule 6: QSOs with the Society's station are worth five points.
    if is_rsgb_station(self.contact.get("Call", "")):
        return 5

    return 1


def show_mults(self):
    """Return display string for mults"""
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
        return contest_points
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, cabrillo_name, "RSGB-CC-CW")


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
                themode = _cabrillo_mode(contact.get("Mode", ""))
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


def recalculate_mults(self):  # pylint: disable=unused-argument
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
            elif self.other_2.text().isnumeric():
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
            else:
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])

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
    return mults


def just_points(self):  # pylint: disable=unused-argument
    """Get points for RTC XML"""
    return get_points(self)
