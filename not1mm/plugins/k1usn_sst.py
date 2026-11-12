"""K1USN Slow Speed Test

Find rules at: http://www.k1usn.com/sst.html

160-10m, once per band.  The exchange is the operator's name and their
state/province/country; each one of those is a multiplier once per band, and a
station outside W/VE is not a country multiplier of its own.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """K1USN Slow Speed Test."""

    DisplayName = "K1USN SLOW SPEED TEST"
    CabrilloName = "K1USNSST"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name + SPC"
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    SendsRTCScore = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryFields = ("field3", "field4")
    FrameText = ("", "Name", "SPC")
    AccessibleNames = ("", "", "Name", "SPC")
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Name",
        "Sect",
        "M1",
        "PTS",
    ]
    PointsPerContact = 1
    # Each state/province/country once per band.
    NumMults = 1
    Multiplier1Name = "SPC"
    MultSqlString = "Sect"
    IsMult1Per = 1

    def mult_sql(self, slot):
        """The section as SQL, dropping the "DX" a non-W/VE station sends."""
        if slot == 1:
            return "CASE WHEN Sect != 'DX' THEN Sect END"
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The state/province/country; "DX" is not one."""
        if slot == 1:
            sect = contact.get("Sect", "")
            return sect if sect and sect != "DX" else None
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The name and state/province/country, and the multiplier mark."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = parent.other_1.text().upper()
        parent.contact["Sect"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        self.mark_multipliers()

    def prefill(self):
        """Nothing to fill: the sent exchange is a fixed setting."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        Both exchange fields -- the name and the SPC -- are needed before the
        contact can be logged, and both are text.
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
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_1.text().isalpha() and parent.other_2.text().isalpha():
                    self._resend_corrected_call(buttons_to_send)
                    parent.make_button_green(parent.esm_dict["QRZ"])
                    buttons_to_send.append(parent.esm_dict["QRZ"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

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

            elif parent.current_widget in ("other_1", "other_2"):
                if parent.other_1.text() == "" or parent.other_2.text() == "":
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])
                elif parent.other_1.text().isalpha() and parent.other_2.text().isalpha():
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])
                    buttons_to_send.append("LOGIT")
                else:
                    parent.make_button_green(parent.esm_dict["AGN"])
                    buttons_to_send.append(parent.esm_dict["AGN"])

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

    def after_recalculate_mults(self):
        """Refresh the log window after a rescore."""
        cmd = {"cmd": "UPDATELOG"}
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def cabrillo_qso_line(self, contact):
        """The SST line: the sent exchange, then their name and SPC."""
        the_date_and_time = contact.get("TS", "")
        loggeddate = the_date_and_time[:10]
        loggedtime = the_date_and_time[11:13] + the_date_and_time[14:16]
        frequency = str(round(contact.get("Freq", "0"))).rjust(5)
        return (
            f"QSO: {frequency} {self.cabrillo_mode(contact.get('Mode', ''))} "
            f"{loggeddate} {loggedtime} "
            f"{contact.get('StationPrefix', '').ljust(13)} "
            f"{str(contact.get('SentNr', '')).upper()} "
            f"{contact.get('Call', '').ljust(13)} "
            f"{str(contact.get('Name', '')).ljust(11)} "
            f"{str(contact.get('Sect', '')).ljust(5)}"
        )

    def ft8_handler(self, the_packet: dict):
        """Process a logged QSO packet from WSJT-X or FlDigi."""
        parent = self.parent
        their_name = the_packet.get("NAME", "").upper()
        their_spc = (
            the_packet.get("STATE", "") or the_packet.get("SRX_STRING", "") or "DX"
        ).upper()
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.other_1.setText(their_name)
        parent.other_2.setText(their_spc)
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = their_name
        parent.contact["Sect"] = their_spc
        parent.contact["Mode"] = the_packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(the_packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(
            float(the_packet.get("FREQ", "0.0")) * 1000, 2
        )
        parent.contact["Band"] = get_logged_band(
            str(int(float(the_packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the call history entry for the callsign being typed."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('Exch1', '')}, {result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the exchange from the call history file, if it has one."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Name', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Exch1', '')}")
