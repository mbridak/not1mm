"""General Logging plugin

A general-logging mode rather than a contest: the exchange is the two reports
plus a name and a free-text comment, there is no scoring and no dupe checking
(``DupeType = 4``).

The Cabrillo export is deliberately empty -- the mode has no sponsor log
format -- so :meth:`Contest.cabrillo` stays a no-op.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band


class Contest(ContestBase):
    """General Logging: reports, name and comment."""

    DisplayName = "General Logging"
    CabrilloName = "General-Logging"
    SortOrder = 50  # a mode, not a contest: keep it at the top of the picker
    Mode = "BOTH"
    DupeType = 4  # no dupe checking
    SupportsFT8 = True
    FrameText = ("SNT", "Name", "Comment")
    AccessibleNames = ("RST Sent", "", "Name", "Comment")
    # A callsign lookup leaves the focus on the name field.
    NextField = "other_1"
    # The name and the comment contain spaces, so a space is text and not a
    # separator in either extra field.
    advance_on_space = [True, True, True, False, False]
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
        "Name",
        "Comment",
    ]

    def interface(self):
        """Label the fields, then keep the exchange free of forced upper case."""
        super().interface()
        # Disable the forced uppercase from main.ui.
        self.parent.other_1.setStyleSheet("text-transform: none;")
        self.parent.other_2.setStyleSheet("text-transform: none;")

    def set_contact_vars(self):
        """Copy the reports, the name and the comment into the contact."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = parent.other_1.text()
        parent.contact["Comment"] = parent.other_2.text()

    def prefill(self):
        """Nothing to prefill: other_1 is the received name."""

    def cabrillo(self, filename, file_encoding):
        """No Cabrillo export: the mode has no sponsor log format."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The contact is finished as soon as one of the exchange fields has been
        typed in; there is nothing to ask the other station to repeat, so this
        does not use the base's empty-field test.
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
                # If the operator corrected a busted callsign after the
                # exchange was already sent, resend the corrected call ahead of
                # the QRZ/TU macro so the other station logs the right
                # callsign before the QSO is wiped.
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
                parent.make_button_green(parent.esm_dict["QRZ"])
                buttons_to_send.append(parent.esm_dict["QRZ"])
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
        parent.contact["SNT"] = packet.get("RST_SENT", "59")
        parent.contact["RCV"] = packet.get("RST_RCVD", "59")
        their_grid = packet.get("GRIDSQUARE", "")
        if their_grid:
            parent.contact["GridSquare"] = their_grid
        if packet.get("SUBMODE"):
            parent.contact["Mode"] = packet.get("SUBMODE", "ERR")
        else:
            parent.contact["Mode"] = packet.get("MODE", "ERR")
        parent.contact["Freq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["QSXFreq"] = round(float(packet.get("FREQ", "0.0")) * 1000, 2)
        parent.contact["Band"] = get_logged_band(
            str(int(float(packet.get("FREQ", "0.0")) * 1000000))
        )
        parent.save_contact()

    def populate_history_info_line(self):
        """Show the call, name and user text for the typed callsign."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(
                f"{result.get('Call', '')}, {result.get('Name', '')}, "
                f"{result.get('UserText', '...')}"
            )
        else:
            parent.history_info.setText("")

    def check_call_history(self):
        """Fill the name from the call history file when it is empty."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_1.text() == "":
                parent.other_1.setText(f"{result.get('Name', '')}")
