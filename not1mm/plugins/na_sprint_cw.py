"""North American Sprint, CW plugin

Find rules at: https://ncjweb.com/Sprint-Rules.pdf

80, 40 and 20m only, once per band.  The exchange is both calls, a serial
number, a name and a location (US state/DC, VE province/territory, another NA
country, or "DX").  A North American station is 1 point and an NA operator
scores every valid QSO while a non-NA operator only scores NA contacts.

Each US state plus DC, each of the 13 VE provinces/territories and each other
North American country is a multiplier once for the whole contest (not per
band).  KH6, FP, 4U1UN, VP9 and OX count as North America.

The sprint's QSY rule: a station that solicits a call (CQ, QRZ, or even just
sending its callsign) may work one station in response and must then move at
least 1 kHz before soliciting again.  So the plugin flips RUN <-> S&P after
each logged QSO and warns while in RUN within 1 kHz of the last run QSO's
frequency.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import logging
import re

from PyQt6 import QtWidgets
from PyQt6.QtCore import QTimer

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)

# 1 once per contest, 2 work each band, 3 each band/mode, 4 no dupe checking
SPRINT_AUTO_RUN_SP = True  # Flip RUN <-> S&P automatically after each QSO.
QSY_KHZ = 1.0  # Minimum QSY after a QSO you solicited, in kHz.

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(parent, call: str) -> tuple:
    """Return (continent, primary_pfx) for a callsign, or ("", "")."""
    if not call or not hasattr(parent, "cty_lookup"):
        return ("", "")
    try:
        result = parent.cty_lookup(call)
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


def _na_country_prefixes(parent) -> set:
    """All non-W/VE cty.dat primary prefixes that count as NA."""
    cache = getattr(_na_country_prefixes, "cache", None)
    if cache is not None:
        return cache
    prefixes = set()
    ctyfile = getattr(parent, "ctyfile", None) or {}
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


def _is_location_token(parent, token: str, call: str, pfx: str) -> bool:
    """Is this exchange token a location rather than a name?"""
    if token in ("DX",) or normalize_location(token) in US_STATES | VE_PROVINCES:
        return True
    if token in _na_country_prefixes(parent):
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


def split_exchange(parent, exchange: str, call: str, pfx: str = "") -> tuple:
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
        if _is_location_token(parent, token, call_out, pfx):
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


def _history_location(result: dict) -> str:
    for field in ("State", "Sect", "Exch1", "Loc1"):
        value = result.get(field, "")
        if value:
            return str(value).upper()
    return ""


def _my_name_loc(parent) -> tuple:
    """Our sent name and location from the contest's Sent Exchange."""
    tokens = [
        t
        for t in parent.contest_settings.get("SentExchange", "").upper().split()
        if t.isalnum() and not t.isdigit()
    ]
    station = getattr(parent, "station", {}) or {}
    my_name = tokens[0] if tokens else station.get("Name", "").split(" ")[0].upper()
    my_loc = tokens[-1] if len(tokens) > 1 else station.get("State", "").upper()
    return (my_name, normalize_location(my_loc))


def _qso_points(parent, call: str, band: str, is_dupe: bool) -> int:
    if is_dupe:
        return 0
    if str(band) not in SPRINT_BANDS:
        return 0
    my_cont, my_pfx = _entity(parent, (getattr(parent, "station", {}) or {}).get("Call", ""))
    if not my_cont or _is_na(my_cont, my_pfx):
        return 1
    his_cont, his_pfx = _entity(parent, call)
    return 1 if _is_na(his_cont, his_pfx) else 0


class Contest(ContestBase):
    """North American Sprint, CW."""

    DisplayName = "NA SPRINT CW"
    CabrilloName = "NA-SPRINT-CW"
    Mode = "CW"
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

    DupeType = 2  # once per band
    SendsRTCScore = True
    SupportsFT8 = True
    # Makes the main window call parse_exchange() on every edit of other_2.
    call_parse_exchange_on_edit = True
    # Only the two exchange fields are used; the RSTs are hidden.
    EntryFields = ("field3", "field4")
    FrameText = ("", "SentNR", "NR Name Loc")
    AccessibleNames = ("", "", "Sent Serial Number", "Serial Number Name Location")
    NextField = "other_2"
    # other_2 is a free-form "NR Name Loc", so a space there is part of the
    # exchange; other_1 is the sent serial and a space still separates.
    advance_on_space = [True, True, True, True, False]
    LogInfo = [
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
    # One multiplier -- the received state/province/country -- counted once for
    # the whole contest, and only a contact that scored a point counts.
    NumMults = 1
    Multiplier1Name = "Exchange"
    MultSqlString = "Exchange"
    IsMult1Per = 4

    # The frequency (kHz) of the last QSO in which we were the soliciting
    # station.  None until this instance has logged a run QSO; the module kept
    # it in a module global.
    _qsy_anchor_khz = None

    def init_contest(self):
        """Set up the entry window and clear the QSY state."""
        self._qsy_anchor_khz = None
        super().init_contest()

    def reset_label(self):
        """Put the exchange label back after a field is cleared."""
        self.parent.exch_label.setText(
            QtWidgets.QApplication.translate("ContestPlugin", "NR Name Loc")
        )

    # -- the exchange --------------------------------------------------------
    def parse_exchange(self):
        """Parse the received exchange field and show what was understood."""
        parent = self.parent
        call = parent.callsign.text().upper()
        pfx = (
            parent.contact.get("CountryPrefix", "")
            if hasattr(parent, "contact")
            else ""
        )
        nr, name_tok, loc, call_out = split_exchange(
            parent, parent.other_2.text(), call, pfx
        )
        label = f"nr:{nr} name:{name_tok} loc:{loc}"
        if call_out != call:
            label = f"call:{call_out} " + label
        if hasattr(parent, "exch_label"):
            parent.exch_label.setText(label)
        return (nr, name_tok, loc, call_out)

    def _exchange_complete(self) -> bool:
        nr, name_tok, loc, _ = self.parse_exchange()
        return bool(nr and name_tok and loc)

    # -- the QSY rule --------------------------------------------------------
    def _vfo_khz(self) -> float:
        try:
            return float(getattr(self.parent, "radio_state", {}).get("vfoa", 0.0)) / 1000
        except (TypeError, ValueError):
            return 0.0

    def qsy_needed(self) -> bool:
        """True if we must move before soliciting again."""
        if self._qsy_anchor_khz is None:
            return False
        vfo = self._vfo_khz()
        if vfo <= 0:
            return False
        return abs(vfo - self._qsy_anchor_khz) < QSY_KHZ

    def _after_log(self, was_run: bool, freq_khz: float):
        """Called right after a QSO is saved. Applies the Sprint QSY rule."""
        parent = self.parent
        if was_run:
            self._qsy_anchor_khz = freq_khz if freq_khz else None
            if hasattr(parent, "set_running"):
                parent.set_running(False)
        else:
            self._qsy_anchor_khz = None
            if hasattr(parent, "set_running"):
                parent.set_running(True)

    def _schedule_after_log(self, was_run: bool, freq_khz: float):
        if not SPRINT_AUTO_RUN_SP:
            return
        if QtWidgets.QApplication.instance() is None:
            return
        QTimer.singleShot(0, lambda: self._after_log(was_run, freq_khz))

    # -- logging -------------------------------------------------------------
    def prefill(self):
        """Fill the sent serial, the Sprint's only sent-exchange field."""
        parent = self.parent
        serial_nr = str(parent.current_sn).zfill(3)
        if serial_nr in ("None", "REQUESTED"):
            serial_nr = "001"
        if len(parent.other_1.text()) == 0:
            parent.other_1.setText(serial_nr)

    def points(self):
        """1 point for a valid QSO; a non-NA operator scores only NA contacts."""
        parent = self.parent
        return _qso_points(
            parent,
            parent.contact.get("Call", ""),
            parent.contact.get("Band", ""),
            parent.contact_is_dupe > 0,
        )

    def mult_sql(self, slot):
        """Only a contact that scored a point and has a location counts."""
        if slot != 1:
            return super().mult_sql(slot)
        return "CASE WHEN Points > 0 AND Exchange1 <> '' THEN Exchange1 END"

    def is_new_mult(self, slot, contact) -> int:
        """The module only checked for a new multiplier on a Sprint band."""
        if slot == 1 and str(contact.get("Band", "")) not in SPRINT_BANDS:
            return 0
        return super().is_new_mult(slot, contact)

    def set_contact_vars(self):
        """The parsed exchange, and the multiplier it is worth."""
        parent = self.parent
        contact = parent.contact
        nr, name_tok, loc, call = self.parse_exchange()
        contact["SNT"] = parent.sent.text()
        contact["RCV"] = parent.receive.text()
        contact["SentNr"] = parent.other_1.text().strip() or 0
        contact["NR"] = nr or 0
        contact["Name"] = name_tok
        contact["Sect"] = loc
        contact["Call"] = call

        # Band normally comes from the radio poll; derive it from the logged
        # frequency if the poll has not filled it in yet.
        if str(contact.get("Band", "")) in ("", "0", "0.0"):
            try:
                freq_khz = float(contact.get("Freq", 0) or 0)
                if freq_khz > 0:
                    contact["Band"] = get_logged_band(str(int(freq_khz * 1000)))
            except (TypeError, ValueError):
                pass

        continent, pfx = _entity(parent, call)
        if not pfx:
            continent = contact.get("Continent", "")
            pfx = contact.get("CountryPrefix", "")
        contact["Exchange1"] = mult_key(loc, continent, pfx)
        self.mark_multipliers()

        was_run = bool(contact.get("IsRunQSO", False))
        self._schedule_after_log(was_run, float(contact.get("Freq", 0) or 0))

    def recalculate_mults(self):
        """Recalculate points and multipliers after a change in the log.

        An imported log carries no Points and no Exchange1, and both depend on
        the contact's position in the log, so the module's replay is kept
        rather than the base's marking-only one.
        """
        parent = self.parent
        all_contacts = parent.database.fetch_all_contacts_asc()
        worked = set()
        mults_seen = set()
        for contact in all_contacts:
            call = contact.get("Call", "")
            band = str(contact.get("Band", ""))
            is_dupe = (call, band) in worked
            worked.add((call, band))
            contact["Points"] = _qso_points(parent, call, band, is_dupe)

            continent, pfx = _entity(parent, call)
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
            parent.database.change_contact(contact)
        self.after_recalculate_mults()

    def after_recalculate_mults(self):
        """Refresh the log window, as the module's replay did."""
        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if getattr(self.parent, "log_window", None):
            self.parent.log_window.msg_from_main(cmd)

    # -- export --------------------------------------------------------------
    def cabrillo_location(self) -> str:
        """LOCATION is the location we sent, not the station's ARRL section."""
        return _my_name_loc(self.parent)[1]

    def cabrillo_category_mode(self) -> str:
        """The Sprint is one mode: the contest's own, not the setup's."""
        return self.Mode

    def cabrillo_mode(self, mode: str) -> str:
        """The sponsor's mode codes: RTTY and its relatives are ``RY``."""
        mode = (mode or "").strip()
        if mode in ("CW", "CW-U", "CW-L", "CW-R", "CWR"):
            return "CW"
        if mode in ("LSB", "USB", "SSB", "AM", "FM"):
            return "PH"
        if mode in (
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
        return mode

    def cabrillo_qso_line(self, contact):
        """The Sprint line: both exchanges, in four parts."""
        parent = self.parent
        my_name, my_loc = _my_name_loc(parent)
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", 0) or 0)).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).rjust(4)} "
            f"{my_name.ljust(10)} "
            f"{my_loc.ljust(3)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('NR', '')).rjust(4)} "
            f"{str(contact.get('Name', '')).upper().ljust(10)} "
            f"{str(contact.get('Sect', '')).upper().ljust(3)}".rstrip()
        )

    # -- ESM -----------------------------------------------------------------
    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine, Sprint flavored."""
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in [
            parent.esm_dict["CQ"],
            parent.esm_dict["EXCH"],
            parent.esm_dict["QRZ"],
            parent.esm_dict["AGN"],
            parent.esm_dict["HISCALL"],
            parent.esm_dict["MYCALL"],
            parent.esm_dict["QSOB4"],
        ]:
            if a_button is not None:
                parent.restore_button_color(a_button)

        buttons_to_send = []
        in_exchange = parent.current_widget in ("other_1", "other_2")

        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.esm_call_sent = ""
                    if self.qsy_needed():
                        # Sprint rule: you solicited and worked one station here.
                        parent.exch_label.setText(
                            f"QSY {QSY_KHZ:g} kHz before CQ!"
                        )
                    else:
                        if parent.exch_label.text().startswith("QSY"):
                            self.reset_label()
                        parent.make_button_green(parent.esm_dict["CQ"])
                        buttons_to_send.append(parent.esm_dict["CQ"])
                else:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif in_exchange:
                if not self._exchange_complete():
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    if (
                        parent.pref.get("esm_send_corrected_call")
                        and parent.esm_call_sent
                        and parent.callsign.text() != parent.esm_call_sent
                    ):
                        parent.make_button_green(parent.esm_dict["HISCALL"])
                        buttons_to_send.append(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif in_exchange:
                if not self._exchange_complete():
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

    # -- call history --------------------------------------------------------
    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{_history_location(result)}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill name and location from call history."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                prefill_text = f"{result.get('Name', '')} {_history_location(result)}"
                prefill_text = prefill_text.strip().upper()
                if prefill_text:
                    parent.other_2.setText(prefill_text + " ")

    # -- FT8 / digital -------------------------------------------------------
    def ft8_handler(self, packet: dict):
        """Log a QSO sent as an ADIF UDP packet (fldigi, MMTTY bridges, etc).

        Serial comes from SRX, name from NAME, location from STATE / VE_PROV /
        SRX_STRING.
        """
        parent = self.parent
        logger.debug("%s", f"{packet=}")
        parent.callsign.setText(packet.get("CALL", ""))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()

        stx = str(packet.get("STX", "")).strip()
        if stx.isdigit() and int(stx) > 0:
            parent.other_1.setText(stx)
        elif not parent.other_1.text():
            current_sn = getattr(parent, "current_sn", None)
            parent.other_1.setText(str(current_sn or 1))

        srx = str(packet.get("SRX", "")).strip()
        srx_string = str(packet.get("SRX_STRING", "")).strip()
        location = (
            packet.get("STATE", "")
            or packet.get("VE_PROV", "")
            or packet.get("ARRL_SECT", "")
        )
        parts = [srx, str(packet.get("NAME", "")).strip(), srx_string, location]
        parent.other_2.setText(" ".join(p for p in parts if p))

        freq_mhz = float(packet.get("FREQ", "0.0") or 0.0)
        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(freq_mhz * 1000, 2)
        parent.contact["QSXFreq"] = round(freq_mhz * 1000, 2)
        parent.contact["Band"] = get_logged_band(str(int(freq_mhz * 1000000)))
        logger.debug("%s", f"{parent.contact=}")
        parent.save_contact()
