"""SSA Manadstest CW plugin

Find rules at: https://hfcontest.ssa.se/ssa-mt/regler.html
"""

# SSA Manadstest - Swedish monthly HF contest, CW mode.
#   Exchange:   RST + serial number + 6-character Maidenhead locator
#   Example:    599 01 JP75XX
#   Multipliers: unique 4-character locator prefixes per band
#   Score:      total QSO points * total multipliers
#   QSO points: 2 per valid QSO

from not1mm.lib.contest import ContestBase, output_cabrillo_line
from not1mm.lib.version import __version__

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


def _validate_field(widget, valid):
    """Color widget red if invalid, reset otherwise"""
    if valid:
        widget.setStyleSheet("")
    else:
        widget.setStyleSheet("background-color: #5c0000;")


def _check_rst(value, rst_min=111, rst_max=599):
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


class Contest(ContestBase):
    """SSA Manadstest, CW."""

    DisplayName = "SSA MT CW"
    CabrilloName = "SSA-MT-CW"
    Mode = "CW"
    EXCHANGE_HINT = "# LocXXXX"
    DupeType = 2  # once per band
    PointsPerContact = 2
    LogInfo = [
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
    FrameText = ("Sent", "Nr", "Locator")
    RcvLabel = "Received"
    AccessibleNames = (
        "Signal Report Sent",
        "",
        "Received Serial Number",
        "Received Locator",
    )
    # Each contacted locator square -- the first four characters of the
    # exchange -- once per band.
    NumMults = 1
    Multiplier1Name = "Exchange"
    MultSqlString = "Exchange"
    IsMult1Per = 1

    # Whether the running exchange has already been sent in this contact; the
    # search-and-pounce half of the ESM machine needs it.
    _exch_sent = False

    def init_contest(self):
        """Setup plugin"""
        self._exch_sent = False
        super().init_contest()

    def interface(self):
        """Setup user interface"""
        super().interface()
        self.parent.sent.setReadOnly(False)

    def set_contact_vars(self):
        """Map UI fields to contact record"""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.current_sn
        parent.contact["GridSquare"] = parent.contest_settings.get("SentExchange", "")
        parent.contact["NR"] = parent.other_1.text()
        parent.contact["Exchange1"] = parent.other_2.text().upper()

    def predupe(self):
        """Pre-fill locator from call history on each callsign keystroke"""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            name = result.get("Name", "") or ""
            loc = result.get("Loc1", "") or ""
            info = ", ".join(x for x in [result.get("Call", ""), name, loc] if x)
            parent.history_info.setText(info)
            parent.other_2.setText(loc)
        else:
            parent.other_2.setText("")
            parent.history_info.setText("")

    def prefill(self):
        """Pre-fill sent RST"""
        if len(self.parent.sent.text()) == 0:
            self.parent.sent.setText("599")

    def mult_sql(self, slot):
        """The locator square is the first four characters of the exchange."""
        if slot == 1:
            return (
                "CASE WHEN typeof(Exchange1) = 'text' "
                "AND LENGTH(Exchange1) >= 4 "
                "THEN SUBSTR(Exchange1, 1, 4) END"
            )
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same key in Python, for the log and the replay."""
        if slot != 1:
            return super().mult_value(slot, contact)
        exchange = str(contact.get("Exchange1", "") or "")
        return exchange[:4].upper() if len(exchange) >= 4 else None

    def get_mults(self):
        """Return mult dict for RTC XML"""
        return {"locator": self.show_mults()}

    def cabrillo_mode(self, mode):
        """The sponsor's mode codes: every digital mode is DG, AM is phone."""
        if mode in ("LSB", "USB", "AM"):
            return "PH"
        if mode in (
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
            return "DG"
        return super().cabrillo_mode(mode)

    def cabrillo_qso_line(self, contact):
        """The SSA line: report, a three-digit serial and two locators."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", 0))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SNT', '')).ljust(3)} "
            f"{str(contact.get('SentNr', '0')).zfill(3)} "
            f"{contact.get('GridSquare', '').ljust(6)} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('RCV', '')).ljust(3)} "
            f"{str(contact.get('NR', '0')).zfill(3)} "
            f"{contact.get('Exchange1', '')}"
        )

    def _cabrillo_header(self, file_descriptor, file_encoding):
        """The SSA header: no LOCATION, and one ADDRESS line per address line."""
        parent = self.parent
        station = parent.station
        settings = parent.contest_settings

        def line(text):
            output_cabrillo_line(text, "\r\n", file_descriptor, file_encoding)

        line("START-OF-LOG: 3.0")
        line(f"CREATED-BY: Not1MM v{__version__}")
        line(f"CONTEST: {self.CabrilloName}")
        if station.get("Club", ""):
            line(f"CLUB: {station.get('Club', '').upper()}")
        line(f"CALLSIGN: {station.get('Call', '')}")
        line(f"CATEGORY-OPERATOR: {settings.get('OperatorCategory', '')}")
        line(f"CATEGORY-ASSISTED: {settings.get('AssistedCategory', '')}")
        line(f"CATEGORY-BAND: {settings.get('BandCategory', '')}")
        line(f"CATEGORY-MODE: {settings.get('ModeCategory', '')}")
        if settings.get("OverlayCategory", "") != "N/A":
            line(f"CATEGORY-OVERLAY: {settings.get('OverlayCategory', '')}")
        line(f"GRID-LOCATOR: {station.get('GridSquare', '')}")
        line(f"CATEGORY-POWER: {settings.get('PowerCategory', '')}")
        line(f"CLAIMED-SCORE: {self.calc_score()}")
        ops = ""
        for op in parent.database.get_ops():
            ops += f"{op.get('Operator', '')}, "
        if station.get("Call", "") not in ops:
            ops += f"@{station.get('Call', '')}"
        else:
            ops = ops.rstrip(", ")
        line(f"OPERATORS: {ops}")
        line(f"NAME: {station.get('Name', '')}")
        line(f"ADDRESS: {station.get('Street1', '')}")
        line(f"ADDRESS: {station.get('City', '')}")
        line(f"ADDRESS: {station.get('Zip', '')}")
        line(f"ADDRESS: {station.get('Country', '')}")
        line(f"ADDRESS: {station.get('Email', '')}")

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM State Machine"""
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        if parent.current_widget == "callsign":
            self._exch_sent = False

        _validate_field(
            parent.sent, not parent.sent.text() or _check_rst(parent.sent.text())
        )
        _validate_field(
            parent.receive,
            not parent.receive.text() or _check_rst(parent.receive.text()),
        )
        _validate_field(
            parent.other_1,
            not parent.other_1.text() or _check_nr(parent.other_1.text()),
        )
        _validate_field(
            parent.other_2,
            not parent.other_2.text() or _check_locator(parent.other_2.text()),
        )

        for a_button in [
            parent.F1,
            parent.F2,
            parent.F3,
            parent.F4,
            parent.F5,
            parent.F6,
            parent.F7,
            parent.F8,
            parent.F9,
            parent.F10,
            parent.F11,
            parent.F12,
        ]:
            parent.restore_button_color(a_button)

        buttons_to_send = []

        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif parent.contact_is_dupe:
                    parent.make_button_green(parent.esm_dict["QSOB4"])
                    buttons_to_send.append(parent.esm_dict["QSOB4"])
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget == "other_1":
                if parent.other_1.text() == "":
                    parent.make_button_green(parent.F11)
                    buttons_to_send.append(parent.F11)
                else:
                    if with_enter is True:
                        parent.other_2.setFocus()
                        return

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
                    parent.make_button_green(parent.F12)
                    buttons_to_send.append(parent.F12)
                else:
                    # If the operator corrected a busted callsign after the
                    # exchange was already sent, resend the corrected call
                    # ahead of the QRZ/TU macro so the other station logs the
                    # right callsign before the QSO is wiped.
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
                            if (
                                not _check_rst(parent.sent.text())
                                or not _check_rst(parent.receive.text())
                                or not _check_nr(parent.other_1.text())
                                or not _check_locator(parent.other_2.text())
                            ):
                                return
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        parent.process_function_key(button)
                if parent.contact_is_dupe:
                    return
                if (
                    parent.current_widget == "callsign"
                    and len(parent.callsign.text()) > 2
                ):
                    parent.other_1.setFocus()
        else:
            if parent.current_widget == "callsign":
                if parent.contact_is_dupe:
                    parent.make_button_green(parent.esm_dict["QSOB4"])
                    buttons_to_send.append(parent.esm_dict["QSOB4"])
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget == "other_1":
                if parent.other_1.text() == "":
                    parent.make_button_green(parent.F11)
                    buttons_to_send.append(parent.F11)
                else:
                    if with_enter is True:
                        parent.other_2.setFocus()
                        return

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
                    parent.make_button_green(parent.F12)
                    buttons_to_send.append(parent.F12)
                elif not self._exch_sent:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    if with_enter is True:
                        self._exch_sent = True
                else:
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            if (
                                not _check_rst(parent.sent.text())
                                or not _check_rst(parent.receive.text())
                                or not _check_nr(parent.other_1.text())
                                or not _check_locator(parent.other_2.text())
                            ):
                                return
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)
                if parent.current_widget == "callsign":
                    parent.other_1.setFocus()

    def populate_history_info_line(self):
        """Fill history info label from call history"""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            name = result.get("Name", "") or ""
            loc = result.get("Loc1", "") or ""
            usertext = result.get("UserText", "") or ""
            info = ", ".join(
                x for x in [result.get("Call", ""), name, loc, usertext] if x
            )
            parent.history_info.setText(info)
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Pre-fill locator from call history if available"""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Loc1', '')}")
