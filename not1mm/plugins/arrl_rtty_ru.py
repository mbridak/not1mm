"""ARRL RTTY Roundup plugin

Find rules at: http://www.arrl.org/rtty-roundup

80/40/20/15/10m, once per band.  The exchange is a state/province (or a serial
from a station outside W/VE), every contact is one point, and each state or
province and each DXCC country is a multiplier once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band


class Contest(ContestBase):
    """ARRL RTTY Roundup."""

    DisplayName = "ARRL RTTY Roundup"
    CabrilloName = "ARRL-RTTY"
    Mode = "RTTY"
    DupeType = 2  # once per band
    EXCHANGE_HINT = "State/Province or #"
    SupportsFT8 = True
    SendsRTCScore = True
    Bands = (3.5, 7, 14, 21, 28)
    FrameText = ("SNT", "SentNR", "State|Prov|SN")
    AccessibleNames = ("RST Sent", "", "Sent Number", "State Province or Serial Number")
    # A state/province (or serial) and a DXCC country, each once per band.
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 2

    def points(self):
        """One point per contact."""
        if self.parent.contact_is_dupe > 0:
            return 0
        return 1

    def show_mults(self, rtc=None):
        """States/provinces once per band, plus DXCC once per band.

        A W/VE station sends its state/province (stored as text) and everyone
        else a serial (stored as an integer), so the two are told apart by
        ``typeof``.
        """
        database = self.parent.database
        contest = database.current_contest
        us_ve = database.exec_sql(
            "select count(DISTINCT(NR || ':' || Mode)) as mult_count "
            f"from dxlog where ContestNR = {contest} and typeof(NR) = 'text';"
        ).get("mult_count", 0)
        dx = database.exec_sql(
            "select count(DISTINCT(CountryPrefix || ':' || Mode)) as mult_count "
            f"from dxlog where ContestNR = {contest} and typeof(NR) = 'integer';"
        ).get("mult_count", 0)
        if rtc is not None:
            return dx, us_ve
        return us_ve + dx

    def get_mults(self):
        """The score page wants the country and the state counts separately."""
        country, state = self.show_mults(rtc=True)
        return {"country": country, "state": state}

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1`` (see §28)."""

    def set_contact_vars(self):
        """The exchange; the received one is a state/province or a serial."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine, with the RTTY HISCALL not re-sending the exchange."""
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget = parent.inputs_dict.get(new_focused_widget)

        for a_button in (
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
        ):
            parent.restore_button_color(a_button)

        buttons_to_send = []
        if parent.pref.get("run_state"):
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                    parent.esm_call_sent = ""
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                else:
                    self._resend_corrected_call(buttons_to_send)
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
                        if button == parent.esm_dict["HISCALL"]:
                            parent.esm_call_sent = parent.callsign.text()
                            parent.process_function_key(button, rttysendrx=False)
                            continue
                        parent.process_function_key(button)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget == "other_2":
                if parent.other_2.text() == "":
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

    def ft8_handler(self, packet):
        """Log a QSO reported by WSJT-X or fldigi over UDP."""
        parent = self.parent
        parent.callsign.setText(packet.get("CALL"))
        parent.contact["Call"] = packet.get("CALL", "")
        parent.contact["SNT"] = packet.get("RST_SENT", "599")
        parent.contact["RCV"] = packet.get("RST_RCVD", "599")

        sent_string = packet.get("STX_STRING", "")
        if sent_string != "":
            parent.contact["SentNr"] = sent_string
            parent.other_1.setText(str(sent_string))
        else:
            parent.contact["SentNr"] = packet.get("STX", "000")
            parent.other_1.setText(str(packet.get("STX", "000")))

        rx_string = packet.get("STATE", "")
        if rx_string != "":
            parent.contact["NR"] = rx_string
            parent.other_2.setText(str(rx_string))
        else:
            parent.contact["NR"] = packet.get("SRX", "000")
            parent.other_2.setText(str(packet.get("SRX", "000")))

        parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

    def populate_history_info_line(self):
        """Show history info if available."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('State', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Prefill the received exchange from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('State', '')}")
