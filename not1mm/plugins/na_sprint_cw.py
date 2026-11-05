"""North American Sprint, CW plugin"""

# pylint: disable=invalid-name, unused-argument, unused-variable, c-extension-no-member, unused-import, global-statement

# North American Sprint, CW
#   Status:             Active
#   Geographic Focus:   North America
#   Participation:      Worldwide
#   Sponsor:            National Contest Journal (NCJ)
#   Mode:               CW (a separate RTTY Sprint uses na_sprint_rtty.py)
#   Bands:              80, 40, 20m only
#   Dates:              Feb & Sep, 0000-0359 UTC (4 hours)
#   Classes:            Single Op only: High (1500W), Low (100W), QRP (5W)
#   Exchange:           Both calls, serial number, name, and location
#                       (US state/DC, VE province/territory, other NA
#                       country abbreviation, or DX for non-NA stations).
#                       e.g.  N6TR K7GM 154 RICK NC
#                             K7GM 122 TREE OR N6TR
#   Work stations:      Once per band
#   QSO Points:         1 point per valid QSO.
#                       Non-NA stations only get credit for NA contacts.
#   Multipliers:        Each US state + DC, each of the 13 VE
#                       provinces/territories, and each other North American
#                       country - counted ONCE for the whole contest (not per
#                       band). Non-NA countries are not multipliers.
#                       KH6, FP, 4U1UN, VP9 and OX are considered NA.
#   Score Calculation:  Total score = QSOs x mults
#   QSY rule:           A station that solicits a call (CQ, QRZ, or even just
#                       sending its callsign) may work ONE station in
#                       response, and must then move at least 1 kHz before
#                       calling or soliciting another station.
#   Upload log at:      https://ncjweb.com (Cabrillo only, within 7 days)
#   Find rules at:      https://ncjweb.com/Sprint-Rules.pdf
#   Cabrillo name:      NA-SPRINT-CW
#
# Entry fields used by this plugin:
#   other_1 (label "SentNR") - your serial number, prefilled automatically.
#   other_2 (label "NR Name Loc") - the received exchange as free text, in any
#       order, e.g. "154 RICK NC". A later token overrides an earlier one, so
#       you can correct a prefilled (call history) value by typing the new one
#       at the end. A full callsign typed here replaces the logged callsign.
#
# Sprint run/S&P automation (see SPRINT_AUTO_RUN_SP below):
#   After logging a QSO you RAN (you solicited), the plugin flips you to S&P,
#   because the frequency now belongs to the station you just worked.
#   After logging a QSO you made in S&P, the plugin flips you to RUN, because
#   you have inherited that frequency.
#   While in RUN within 1 kHz of the frequency of your last run QSO, ESM will
#   not send CQ and the exchange label shows a QSY warning.

import datetime
import logging
import re

from pathlib import Path

from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer

from not1mm.lib.ham_utility import get_logged_band
from not1mm.lib.plugin_common import gen_adif, imp_adif, get_points, online_score_xml
from not1mm.lib.version import __version__

logger = logging.getLogger(__name__)

EXCHANGE_HINT = "Name Loc  e.g. DAVE MN"

SOAPBOX_HINT = """Sprint macros (the station that will QSY sends both calls first,
the station that stays ends with its own call):
Run  F1 CQ:   NA {MYCALL}
Run  F2:      {HISCALL}
Run  F3 Exch: {MYCALL} {SENTNR} {EXCH}
Run  F4 TU:   TU
S&P  F3 Exch: {HISCALL} {SENTNR} {EXCH} {MYCALL}
S&P  F5:      {MYCALL}
"""

ALTEREGO = None

name = "NA SPRINT CW"
cabrillo_name = "NA-SPRINT-CW"
mode = "CW"  # CW SSB BOTH RTTY

columns = [
    "YYYY-MM-DD HH:MM:SS",
    "Call",
    "Freq",
    "SentNr",
    "RcvNr",
    "Name",
    "Sect",
    "M1",
    "PTS",
]

# callsign, sent, receive, other_1, other_2
# other_1 (SentNR) advances on space, other_2 (free-form exchange) does not.
advance_on_space = [True, True, True, True, False]

# Makes the main window call parse_exchange() on every edit of other_2.
call_parse_exchange_on_edit = True

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
dupe_type = 2

# Flip RUN <-> S&P automatically after each logged QSO (Sprint QSY rule).
SPRINT_AUTO_RUN_SP = True

# Minimum QSY after a QSO you solicited, in kHz.
QSY_KHZ = 1.0

SPRINT_BANDS = ("3.5", "7.0", "14.0")

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}  # fmt: skip

VE_PROVINCES = {
    "BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL",
    "YT", "NT", "NU",
}  # fmt: skip

# Common alternate spellings, normalized to the codes above.
LOCATION_ALIASES = {
    "NF": "NL",
    "LB": "NL",
    "NFL": "NL",
    "PQ": "QC",
    "QU": "QC",
    "PEI": "PE",
    "YU": "YT",
    "NWT": "NT",
}

# cty.dat primary prefixes of the US and Canada. A W/VE station that sends an
# unknown location is not a multiplier.
W_VE_PREFIXES = {"K", "VE"}

# cty.dat puts these outside NA, but the Sprint rules count them as NA.
FORCED_NA_PREFIXES = {"KH6"}

# Entities that are US states, not countries, when the location is missing
# or sent as the prefix.
PREFIX_TO_STATE = {"KL": "AK", "KH6": "HI"}

CALLSIGN_RE = re.compile(
    r"^(?:[A-Z0-9]{1,3}/)?[A-Z0-9]{1,3}[0-9][A-Z]{1,4}(?:/[A-Z0-9]+)?$"
)

# Frequency (kHz) of the last QSO in which we were the soliciting station.
_qsy_anchor_khz = None


def init_contest(self):
    """setup plugin"""
    global _qsy_anchor_khz
    _qsy_anchor_khz = None
    set_tab_next(self)
    set_tab_prev(self)
    interface(self)
    self.next_field = self.other_2


def interface(self):
    """Setup user interface"""
    self.field1.hide()
    self.field2.hide()
    self.field3.show()
    self.field4.show()
    self.other_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "SentNR")
    )
    self.other_1.setAccessibleName("Sent Serial Number")
    self.exch_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "NR Name Loc")
    )
    self.other_2.setAccessibleName("Serial Number Name Location")


def reset_label(self):
    """reset label after field cleared"""
    self.exch_label.setText(
        QtWidgets.QApplication.translate("ContestPlugin", "NR Name Loc")
    )


def set_tab_next(self):
    """Set TAB Advances"""
    self.tab_next = {
        self.callsign: self.other_2,
        self.other_1: self.other_2,
        self.other_2: self.callsign,
    }


def set_tab_prev(self):
    """Set TAB Advances"""
    self.tab_prev = {
        self.callsign: self.other_1,
        self.other_1: self.callsign,
        self.other_2: self.callsign,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(self, call: str) -> tuple:
    """Return (continent, primary_pfx) for a callsign, or ("", "")."""
    if not call or not hasattr(self, "cty_lookup"):
        return ("", "")
    try:
        result = self.cty_lookup(call)
        if result:
            item = result.get(next(iter(result)))
            return (item.get("continent", ""), item.get("primary_pfx", ""))
    except (StopIteration, AttributeError, TypeError):
        pass
    return ("", "")


def _is_na(continent: str, pfx: str) -> bool:
    """True if the entity counts as North America for the Sprint."""
    return continent == "NA" or pfx in FORCED_NA_PREFIXES


def normalize_location(loc: str) -> str:
    """Upper-case a location and map known aliases."""
    loc = (loc or "").strip().upper()
    return LOCATION_ALIASES.get(loc, loc)


def mult_key(sect: str, continent: str, pfx: str) -> str:
    """
    Return the multiplier this QSO represents, or "" for none.

    States/DC/provinces are returned as their abbreviation. Other North
    American countries are returned as "C-<cty primary prefix>" so that e.g.
    the Dominican Republic (HI) cannot collide with Hawaii (HI).
    """
    sect = normalize_location(sect)
    if sect in US_STATES or sect in VE_PROVINCES:
        return sect
    if pfx in PREFIX_TO_STATE:
        return PREFIX_TO_STATE[pfx]
    if not pfx or pfx in W_VE_PREFIXES:
        return ""
    if _is_na(continent, pfx):
        return f"C-{pfx}"
    return ""


def _na_country_prefixes(self) -> set:
    """All non-W/VE cty.dat primary prefixes that count as NA."""
    cache = getattr(_na_country_prefixes, "cache", None)
    if cache is not None:
        return cache
    prefixes = set()
    ctyfile = getattr(self, "ctyfile", None) or {}
    try:
        for item in ctyfile.values():
            pfx = item.get("primary_pfx", "")
            if _is_na(item.get("continent", ""), pfx) and pfx not in W_VE_PREFIXES:
                prefixes.add(pfx)
    except AttributeError:
        pass
    if prefixes:
        _na_country_prefixes.cache = prefixes
    return prefixes


def _is_location_token(self, token: str, call: str, pfx: str) -> bool:
    """Is this exchange token a location rather than a name?"""
    if token in ("DX",) or normalize_location(token) in US_STATES | VE_PROVINCES:
        return True
    if token in _na_country_prefixes(self):
        return True
    # A non-W/VE NA station sending its own prefix, e.g. CO8LY sending "CO".
    if (
        pfx
        and pfx not in W_VE_PREFIXES
        and pfx not in PREFIX_TO_STATE
        and call
        and call.startswith(token)
    ):
        return True
    return False


def split_exchange(self, exchange: str, call: str, pfx: str = "") -> tuple:
    """
    Split a free-form received exchange into (nr, name, loc, call).

    Later tokens override earlier ones, so corrections can be typed at the end.
    """
    nr = ""
    name_tok = ""
    call_out = call
    alpha_tokens = []
    loc_candidates = []

    for token in exchange.upper().split():
        if token.isdigit():
            nr = str(int(token))
            continue
        if _is_location_token(self, token, call_out, pfx):
            loc_candidates.append(token)
            alpha_tokens.append(token)
            continue
        if token.isalpha():
            alpha_tokens.append(token)
            continue
        if CALLSIGN_RE.match(token):
            call_out = token
            continue
        # Anything else alphanumeric (e.g. KP4, VP9) is a location.
        loc_candidates.append(token)
        alpha_tokens.append(token)

    loc = loc_candidates[-1] if loc_candidates else ""
    # Name: the last alpha token that is not a location...
    for token in reversed(alpha_tokens):
        if token not in loc_candidates:
            name_tok = token
            break
    else:
        # ...or, if every token looks like a location (AL, DE, ...), the
        # last one that is not the chosen location.
        remaining = list(alpha_tokens)
        if loc in remaining:
            remaining.remove(loc)
        if remaining:
            name_tok = remaining[-1]

    return (nr, name_tok, normalize_location(loc), call_out)


def parse_exchange(self):
    """Parse the received exchange field and show what was understood."""
    call = self.callsign.text().upper()
    pfx = self.contact.get("CountryPrefix", "") if hasattr(self, "contact") else ""
    nr, name_tok, loc, call_out = split_exchange(self, self.other_2.text(), call, pfx)
    label = f"nr:{nr} name:{name_tok} loc:{loc}"
    if call_out != call:
        label = f"call:{call_out} " + label
    if hasattr(self, "exch_label"):
        self.exch_label.setText(label)
    return (nr, name_tok, loc, call_out)


def _exchange_complete(self) -> bool:
    nr, name_tok, loc, _ = parse_exchange(self)
    return bool(nr and name_tok and loc)


def _vfo_khz(self) -> float:
    try:
        return float(getattr(self, "radio_state", {}).get("vfoa", 0.0)) / 1000
    except (TypeError, ValueError):
        return 0.0


def qsy_needed(self) -> bool:
    """True if we must move before soliciting again."""
    if _qsy_anchor_khz is None:
        return False
    vfo = _vfo_khz(self)
    if vfo <= 0:
        return False
    return abs(vfo - _qsy_anchor_khz) < QSY_KHZ


def _after_log(self, was_run: bool, freq_khz: float):
    """Called right after a QSO is saved. Applies the Sprint QSY rule."""
    global _qsy_anchor_khz
    if was_run:
        _qsy_anchor_khz = freq_khz if freq_khz else None
        if hasattr(self, "set_running"):
            self.set_running(False)
    else:
        _qsy_anchor_khz = None
        if hasattr(self, "set_running"):
            self.set_running(True)


def _schedule_after_log(self, was_run: bool, freq_khz: float):
    if not SPRINT_AUTO_RUN_SP:
        return
    if QtWidgets.QApplication.instance() is None:
        return
    QTimer.singleShot(0, lambda: _after_log(self, was_run, freq_khz))


def _my_name_loc(self) -> tuple:
    """Our sent name and location from the contest's Sent Exchange."""
    tokens = [
        t
        for t in self.contest_settings.get("SentExchange", "").upper().split()
        if t.isalnum() and not t.isdigit()
    ]
    station = getattr(self, "station", {}) or {}
    my_name = tokens[0] if tokens else station.get("Name", "").split(" ")[0].upper()
    my_loc = tokens[-1] if len(tokens) > 1 else station.get("State", "").upper()
    return (my_name, normalize_location(my_loc))


def _qso_points(self, call: str, band: str, is_dupe: bool) -> int:
    if is_dupe:
        return 0
    if str(band) not in SPRINT_BANDS:
        return 0
    my_cont, my_pfx = _entity(
        self, (getattr(self, "station", {}) or {}).get("Call", "")
    )
    if not my_cont or _is_na(my_cont, my_pfx):
        return 1
    his_cont, his_pfx = _entity(self, call)
    return 1 if _is_na(his_cont, his_pfx) else 0


# ---------------------------------------------------------------------------
# Plugin API
# ---------------------------------------------------------------------------


def set_contact_vars(self):
    """Contest Specific"""
    nr, name_tok, loc, call = parse_exchange(self)
    self.contact["SNT"] = self.sent.text()
    self.contact["RCV"] = self.receive.text()
    self.contact["SentNr"] = self.other_1.text().strip() or 0
    self.contact["NR"] = nr or 0
    self.contact["Name"] = name_tok
    self.contact["Sect"] = loc
    self.contact["Call"] = call

    # Band normally comes from the radio poll; derive it from the logged
    # frequency if the poll has not filled it in yet.
    if str(self.contact.get("Band", "")) in ("", "0", "0.0"):
        try:
            freq_khz = float(self.contact.get("Freq", 0) or 0)
            if freq_khz > 0:
                self.contact["Band"] = get_logged_band(str(int(freq_khz * 1000)))
        except (TypeError, ValueError):
            pass

    continent, pfx = _entity(self, call)
    if not pfx:
        continent = self.contact.get("Continent", "")
        pfx = self.contact.get("CountryPrefix", "")
    key = mult_key(loc, continent, pfx)
    self.contact["Exchange1"] = key
    self.contact["IsMultiplier1"] = 0
    if key and str(self.contact.get("Band", "")) in SPRINT_BANDS:
        result = self.database.exec_sql(
            "select count(*) as mult_count from dxlog "
            "where Exchange1 = ? and Points > 0 and ContestNR = ?;",
            (key, self.database.current_contest),
        )
        if not (result or {}).get("mult_count", 0):
            self.contact["IsMultiplier1"] = 1

    was_run = bool(self.contact.get("IsRunQSO", False))
    _schedule_after_log(self, was_run, float(self.contact.get("Freq", 0) or 0))


def predupe(self):
    """called after callsign entered"""


def prefill(self):
    """Fill SentNR"""
    serial_nr = str(self.current_sn).zfill(3)
    if serial_nr in ("None", "REQUESTED"):
        serial_nr = "001"
    if len(self.other_1.text()) == 0:
        self.other_1.setText(serial_nr)


def points(self):
    """Calc point"""
    return _qso_points(
        self,
        self.contact.get("Call", ""),
        self.contact.get("Band", ""),
        self.contact_is_dupe > 0,
    )


def show_mults(self):
    """Return display string for mults"""
    result = self.database.exec_sql(
        "select count(DISTINCT(Exchange1)) as mults from dxlog "
        "where ContestNR = ? and Exchange1 != '' and Points > 0;",
        (self.database.current_contest,),
    )
    if result:
        return int(result.get("mults", 0) or 0)
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
        return int(score) * show_mults(self)
    return 0


def adif(self):
    """Call the generate ADIF function"""
    gen_adif(self, self.contest.cabrillo_name, self.contest.cabrillo_name)


def output_cabrillo_line(line_to_output, ending, file_descriptor, file_encoding):
    """"""
    print(
        line_to_output.encode(file_encoding, errors="ignore").decode(),
        end=ending,
        file=file_descriptor,
    )


def cabrillo_mode(themode: str) -> str:
    """Map a logged mode to a Cabrillo mode."""
    themode = (themode or "").strip()
    if themode in ("CW", "CW-U", "CW-L", "CW-R", "CWR"):
        return "CW"
    if themode in ("LSB", "USB", "SSB", "AM", "FM"):
        return "PH"
    if themode in (
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
        "FSK",
        "FSK-R",
    ):
        return "RY"
    return themode


def cabrillo(self, file_encoding):
    """Generates Cabrillo file."""
    contest_name = self.contest.cabrillo_name
    logger.debug("******Cabrillo*****")
    logger.debug("Station: %s", f"{self.station}")
    logger.debug("Contest: %s", f"{self.contest_settings}")
    now = datetime.datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = (
        str(Path.home())
        + "/"
        + f"{self.station.get('Call', '').upper().replace('/', '-')}_{contest_name}_{date_time}.log"
    )
    logger.debug("%s", filename)
    log = self.database.fetch_all_contacts_asc()
    my_name, my_loc = _my_name_loc(self)
    try:
        with open(filename, "w", encoding=file_encoding, newline="") as file_descriptor:

            def out(line):
                output_cabrillo_line(line, "\r\n", file_descriptor, file_encoding)

            out("START-OF-LOG: 3.0")
            out(f"CREATED-BY: Not1MM v{__version__}")
            out(f"CONTEST: {contest_name}")
            if self.station.get("Club", ""):
                out(f"CLUB: {self.station.get('Club', '').upper()}")
            out(f"CALLSIGN: {self.station.get('Call', '')}")
            out(f"LOCATION: {my_loc}")
            out(
                f"CATEGORY-OPERATOR: {self.contest_settings.get('OperatorCategory', '')}"
            )
            out(
                f"CATEGORY-ASSISTED: {self.contest_settings.get('AssistedCategory', '')}"
            )
            out(f"CATEGORY-BAND: {self.contest_settings.get('BandCategory', '')}")
            out(f"CATEGORY-MODE: {self.contest.mode}")
            out(
                f"CATEGORY-TRANSMITTER: {self.contest_settings.get('TransmitterCategory', '')}"
            )
            if self.contest_settings.get("OverlayCategory", "") not in ("", "N/A"):
                out(
                    f"CATEGORY-OVERLAY: {self.contest_settings.get('OverlayCategory', '')}"
                )
            out(f"GRID-LOCATOR: {self.station.get('GridSquare', '')}")
            out(f"CATEGORY-POWER: {self.contest_settings.get('PowerCategory', '')}")
            out(f"CLAIMED-SCORE: {calc_score(self)}")
            ops = ""
            list_of_ops = self.database.get_ops()
            for op in list_of_ops:
                ops += f"{op.get('Operator', '')}, "
            if self.station.get("Call", "") not in ops:
                ops += f"@{self.station.get('Call', '')}"
            else:
                ops = ops.rstrip(", ")
            out(f"OPERATORS: {ops}")
            out(f"NAME: {self.station.get('Name', '')}")
            out(f"ADDRESS: {self.station.get('Street1', '')}")
            out(f"ADDRESS-CITY: {self.station.get('City', '')}")
            out(f"ADDRESS-STATE-PROVINCE: {self.station.get('State', '')}")
            out(f"ADDRESS-POSTALCODE: {self.station.get('Zip', '')}")
            out(f"ADDRESS-COUNTRY: {self.station.get('Country', '')}")
            out(f"EMAIL: {self.station.get('Email', '')}")
            # QSO: freq  mo date       time call          nr   name       loc call          nr   name       loc
            # QSO:  3548 CW 2026-09-13 0000 N6TR             1 TREE       OR  K7GM             1 RICK       NC
            for contact in log:
                the_date_and_time = contact.get("TS", "")
                themode = cabrillo_mode(contact.get("Mode", ""))
                frequency = str(round(contact.get("Freq", 0) or 0)).rjust(5)
                loggeddate = the_date_and_time[:10]
                loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
                out(
                    f"QSO: {frequency} {themode} {loggeddate} {loggedtime} "
                    f"{contact.get('StationPrefix', '').ljust(13)} "
                    f"{str(contact.get('SentNr', '')).rjust(4)} "
                    f"{my_name.ljust(10)} "
                    f"{my_loc.ljust(3)} "
                    f"{contact.get('Call', '').ljust(13)} "
                    f"{str(contact.get('NR', '')).rjust(4)} "
                    f"{str(contact.get('Name', '')).upper().ljust(10)} "
                    f"{str(contact.get('Sect', '')).upper().ljust(3)}".rstrip()
                )
            out("END-OF-LOG:")
        self.show_message_box(f"Cabrillo saved to: {filename}")
    except IOError as exception:
        logger.critical("cabrillo: IO error: %s, writing to %s", exception, filename)
        self.show_message_box(f"Error saving Cabrillo: {exception} {filename}")
        return


def recalculate_mults(self):
    """Recalculates dupes, points and multipliers after a change in the log."""
    all_contacts = self.database.fetch_all_contacts_asc()
    worked = set()
    mults_seen = set()
    for contact in all_contacts:
        call = contact.get("Call", "")
        band = str(contact.get("Band", ""))
        is_dupe = (call, band) in worked
        worked.add((call, band))
        contact["Points"] = _qso_points(self, call, band, is_dupe)

        continent, pfx = _entity(self, call)
        if not pfx:
            continent = contact.get("Continent", "")
            pfx = contact.get("CountryPrefix", "")
        key = mult_key(contact.get("Sect", ""), continent, pfx)
        contact["Exchange1"] = key
        if key and contact["Points"] > 0 and key not in mults_seen:
            contact["IsMultiplier1"] = 1
            mults_seen.add(key)
        else:
            contact["IsMultiplier1"] = 0
        self.database.change_contact(contact)
    cmd = {}
    cmd["cmd"] = "UPDATELOG"
    if getattr(self, "log_window", None):
        self.log_window.msg_from_main(cmd)


def process_esm(self, new_focused_widget=None, with_enter=False):
    """ESM State Machine, Sprint flavored."""

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
    in_exchange = self.current_widget in ("other_1", "other_2")

    if self.pref.get("run_state"):
        if self.current_widget == "callsign":
            if len(self.callsign.text()) < 3:
                self.esm_call_sent = ""
                if qsy_needed(self):
                    # Sprint rule: you solicited and worked one station here.
                    self.exch_label.setText(f"QSY {QSY_KHZ:g} kHz before CQ!")
                else:
                    if self.exch_label.text().startswith("QSY"):
                        reset_label(self)
                    self.make_button_green(self.esm_dict["CQ"])
                    buttons_to_send.append(self.esm_dict["CQ"])
            else:
                self.make_button_green(self.esm_dict["HISCALL"])
                self.make_button_green(self.esm_dict["EXCH"])
                buttons_to_send.append(self.esm_dict["HISCALL"])
                buttons_to_send.append(self.esm_dict["EXCH"])

        elif in_exchange:
            if not _exchange_complete(self):
                self.make_button_green(self.esm_dict["AGN"])
                buttons_to_send.append(self.esm_dict["AGN"])
            else:
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

        elif in_exchange:
            if not _exchange_complete(self):
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
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(
            f"{result.get('Call', '')}, {result.get('Name', '')}, "
            f"{_history_location(result)}, {result.get('UserText', '...')}"
        )
    else:
        self.history_info.setText("")


def _history_location(result: dict) -> str:
    for field in ("State", "Sect", "Exch1", "Loc1"):
        value = result.get(field, "")
        if value:
            return str(value).upper()
    return ""


def check_call_history(self):
    """Prefill name and location from call history."""
    result = self.database.fetch_call_history(self.callsign.text())
    if result:
        self.history_info.setText(f"{result.get('UserText', '')}")
        if self.other_2.text() == "":
            prefill_text = f"{result.get('Name', '')} {_history_location(result)}"
            prefill_text = prefill_text.strip().upper()
            if prefill_text:
                self.other_2.setText(prefill_text + " ")


def set_self(the_outie):
    """..."""
    globals()["ALTEREGO"] = the_outie


def ft8_handler(the_packet: dict):
    """
    Log a QSO sent as an ADIF UDP packet (fldigi, MMTTY bridges, etc.).

    Serial comes from SRX, name from NAME, location from STATE / VE_PROV /
    SRX_STRING.
    """
    logger.debug(f"{the_packet=}")
    if ALTEREGO is None:
        return
    ALTEREGO.callsign.setText(the_packet.get("CALL", ""))
    ALTEREGO.contact["Call"] = the_packet.get("CALL", "")
    ALTEREGO.contact["SNT"] = ALTEREGO.sent.text()
    ALTEREGO.contact["RCV"] = ALTEREGO.receive.text()

    stx = str(the_packet.get("STX", "")).strip()
    if stx.isdigit() and int(stx) > 0:
        ALTEREGO.other_1.setText(stx)
    elif not ALTEREGO.other_1.text():
        current_sn = getattr(ALTEREGO, "current_sn", None)
        ALTEREGO.other_1.setText(str(current_sn or 1))

    srx = str(the_packet.get("SRX", "")).strip()
    srx_string = str(the_packet.get("SRX_STRING", "")).strip()
    location = (
        the_packet.get("STATE", "")
        or the_packet.get("VE_PROV", "")
        or the_packet.get("ARRL_SECT", "")
    )
    parts = [srx, str(the_packet.get("NAME", "")).strip(), srx_string, location]
    ALTEREGO.other_2.setText(" ".join(p for p in parts if p))

    freq_mhz = float(the_packet.get("FREQ", "0.0") or 0.0)
    ALTEREGO.contact["Mode"] = the_packet.get("MODE", "ERR")
    ALTEREGO.contact["Freq"] = round(freq_mhz * 1000, 2)
    ALTEREGO.contact["QSXFreq"] = round(freq_mhz * 1000, 2)
    ALTEREGO.contact["Band"] = get_logged_band(str(int(freq_mhz * 1000000)))
    logger.debug(f"{ALTEREGO.contact=}")
    ALTEREGO.save_contact()


def get_mults(self):
    """Get mults for RTC XML"""
    mults = {}
    mults["state"] = show_mults(self)
    return mults


def just_points(self):
    """Get points for RTC XML"""
    return get_points(self)
