"""CWT plugin

Find rules at: https://cwops.org/cwops-tests/

160-10m, once per band.  The exchange is the member's name and their member
number (or "CWA" for a non-member); each callsign worked is a multiplier once
for the contest.
"""

import logging

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band

logger = logging.getLogger(__name__)


class Contest(ContestBase):
    """CWops Test (CWT)."""

    DisplayName = "CWT"
    CabrilloName = "CW-OPS"
    Mode = "CW"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name + Member No./'CWA'"
    DupeType = 2  # once per band
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    SupportsFT8 = True
    SendsRTCScore = True
    # The reports are hidden; only the two exchange fields are shown.
    EntryFields = ("field3", "field4")
    FrameText = ("SNT", "Name", "Number or State")
    AccessibleNames = ("RST Sent", "", "Name", "Number or State")
    NextField = "other_1"
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "PTS",
    ]
    PointsPerContact = 1
    # Each callsign once for the contest.
    NumMults = 1
    Multiplier1Name = "Calls"
    MultSqlString = "CallSign"
    IsMult1Per = 4

    def set_contact_vars(self):
        """The member's name and number; the sent exchange is a setting."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = parent.other_1.text().upper()
        parent.contact["NR"] = (
            parent.other_1.text().upper() + " " + parent.other_2.text().upper()
        )
        parent.contact["SentNr"] = parent.contest_settings.get(
            "SentExchange", ""
        ).upper()
        self.mark_multipliers()

    def prefill(self):
        """Nothing to fill: the sent exchange is a fixed setting."""

    def predupe(self):
        """Recall the name and number from an earlier CWT QSO."""
        parent = self.parent
        if parent.other_1.text() == "" and parent.other_2.text() == "":
            call = parent.callsign.text().upper()
            result = parent.database.exec_sql(
                "select NR from dxlog where Call = ? and ContestName = 'CWOPS-CWT' "
                "order by TS desc;",
                (call,),
            )
            if result:
                parts = str(result.get("NR", "")).upper().split()
                if len(parts) == 2:
                    parent.other_1.setText(parts[0])
                    parent.other_2.setText(parts[1])

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The contact needs *both* exchange fields -- the member's name and their
        number or state -- before it can be logged.
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

    def ft8_handler(self, the_packet: dict):
        """Process a logged QSO packet from WSJT-X or FlDigi."""
        parent = self.parent
        their_name = the_packet.get("NAME", "").upper()
        their_nr = (
            the_packet.get("SRX_STRING", "") or the_packet.get("SRX", "")
        ).upper()
        parent.callsign.setText(the_packet.get("CALL", ""))
        parent.other_1.setText(their_name)
        parent.other_2.setText(their_nr)
        parent.contact["Call"] = the_packet.get("CALL", "")
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = their_name
        parent.contact["NR"] = f"{their_name} {their_nr}"
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
