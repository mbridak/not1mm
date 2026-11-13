"""Weekly RTTY Test (WRT)

Find rules at: https://radiosport.world/wrt.html

80m to 10m, once per band, RTTY.  The exchange is a name and a
state/province/country, and every station worked is a multiplier once for the
contest.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band


class Contest(ContestBase):
    """Weekly RTTY Test."""

    DisplayName = "WEEKLY RTTY TEST"
    CabrilloName = "WRT"
    Mode = "RTTY"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name + SPC"
    DupeType = 2  # work each band once
    SupportsFT8 = True
    SendsRTCScore = True
    PointsPerContact = 1
    Bands = (3.5, 7, 14, 21, 28)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Exchange1",
        "M1",
        "PTS",
    ]
    # The reports are not part of this contest's exchange.
    EntryFields = ("field3", "field4")
    FrameText = ("", "Name", "SPC")
    AccessibleNames = ("", "", "Name", "SPC")
    NextField = "other_1"
    # Each callsign worked, once for the whole contest.
    NumMults = 1
    Multiplier1Name = "CallSign"
    MultSqlString = "CallSign"
    IsMult1Per = 4

    def set_contact_vars(self):
        """The exchange, the combined key for the QSO line, and the multiplier."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = parent.other_1.text().upper()
        parent.contact["Sect"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        parent.contact["Exchange1"] = (
            f"{parent.other_1.text().upper()} {parent.other_2.text().upper()}"
        )
        self.mark_multipliers()

    def prefill(self):
        """`other_1` is the *received* name, so the sent exchange is the setup's."""

    def after_recalculate_mults(self):
        """Refresh the log window, as the module's replay did."""
        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The exchange is a name *and* a state/province/country, so both entry
        fields have to be filled with letters before the contact is finished,
        and the macros go to fldigi as one string.
        """
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

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_2.text() == "" or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif (
                    parent.other_1.text().isalpha() and parent.other_2.text().isalpha()
                ):
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                sendstring = ""
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            parent.esm_call_sent = ""
                            continue
                        if button == parent.esm_dict.get("HISCALL"):
                            parent.esm_call_sent = parent.callsign.text()
                        sendstring = (
                            f"{sendstring}{parent.process_macro(button.toolTip())} "
                        )
                parent.fldigi_util.send_string(sendstring)
        else:
            if parent.current_widget == "callsign":
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_2.text() == "" or parent.other_1.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif (
                    parent.other_1.text().isalpha() and parent.other_2.text().isalpha()
                ):
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                sendstring = ""
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        sendstring = (
                            f"{sendstring}{parent.process_macro(button.toolTip())} "
                        )
                parent.fldigi_util.send_string(sendstring)

    def ft8_handler(self, the_packet: dict):
        """Process an FT8/digital QSO packet for this contest."""
        parent = self.parent
        parent.callsign.setText(the_packet.get("CALL"))
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Exchange1"] = the_packet.get("SRX_STRING", "")
        if " " in str(the_packet.get("SRX_STRING", "")):
            exch1, exch2 = str(the_packet.get("SRX_STRING", "")).strip().split(" ")
            parent.other_1.setText(exch1)
            parent.other_2.setText(exch2)
        parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        result = parent.database.fetch_call_exists(the_packet.get("CALL", ""))
        parent.contact["IsMultiplier1"] = 0 if result.get("call_count", "") else 1
        parent.save_contact()

    def cabrillo_qso_line(self, contact):
        """The WRT line: the sent exchange, then the received name and SPC."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        exch1 = ""
        exch2 = ""
        if " " in str(contact.get("Exchange1", "")):
            exch1, exch2 = str(contact.get("Exchange1", "")).strip().split(" ")
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).upper()} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{exch1.ljust(10)} "
            f"{exch2.ljust(5)} "
        )

    def populate_history_info_line(self):
        """Show what the call history file knows about this call."""
        result = self.parent.database.fetch_call_history(self.parent.callsign.text())
        if result:
            self.parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Sect', '')}, {result.get('UserText', '...')}"
            )
        else:
            self.parent.history_info.setText("")

    def check_call_history(self):
        """Fill the exchange from the call history file when it is empty."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Name', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Sect', '')}")
