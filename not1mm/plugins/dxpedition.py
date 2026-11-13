"""DX-Pedition plugin

A general-logging mode rather than a contest: the exchange is the two reports,
there is no scoring and no dupe checking, so the same station may be worked on
the same band as often as the operator likes (``DupeType = 4``).

The Cabrillo export is deliberately empty -- the mode has no sponsor log
format -- so :meth:`Contest.cabrillo` stays a no-op.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase
from not1mm.lib.ham_utility import get_logged_band


class Contest(ContestBase):
    """DX-Pedition: RST sent, RST received, nothing else."""

    DisplayName = "DX-Pedition"
    CabrilloName = "DX-Pedition"
    SortOrder = 60  # a mode, not a contest: keep it at the top of the picker
    Mode = "BOTH"
    DupeType = 4  # no dupe checking
    SupportsFT8 = True
    # Only the two report fields are used.
    EntryFields = ("field1", "field2")
    FrameText = ("SNT", "", "")
    AccessibleNames = ("RST Sent", "", "", "")
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Mode",
        "Snt",
        "Rcv",
    ]
    # A callsign lookup leaves the focus on the received report, not on an
    # exchange field.
    NextField = "receive"

    def init_contest(self):
        """Start in run mode, with no call remembered yet."""
        self.parent.set_running(True)
        self.prev_call = ""
        super().init_contest()

    def reset_label(self):
        """Forget the remembered call when the callsign field is cleared."""
        self.prev_call = ""

    def set_contact_vars(self):
        """Copy the two reports into the contact."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()

    def prefill(self):
        """Nothing to prefill: this mode sends no exchange."""

    def cabrillo(self, filename, file_encoding):
        """No Cabrillo export: the mode has no sponsor log format."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        A general-logging contact is over as soon as the call has been copied
        once: the first Enter after a call sends HISCALL and the exchange, the
        next sends QRZ and logs.  Nothing runs in search-and-pounce, which is
        why this is not the base's machine.
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
                elif len(parent.callsign.text()) > 2:
                    if self.prev_call == "":
                        parent.make_button_green(parent.esm_dict["HISCALL"])
                        parent.make_button_green(parent.esm_dict["EXCH"])
                        buttons_to_send.append(parent.esm_dict["HISCALL"])
                        buttons_to_send.append(parent.esm_dict["EXCH"])
                    elif self.prev_call != parent.callsign.text():
                        parent.make_button_green(parent.esm_dict["HISCALL"])
                        parent.make_button_green(parent.esm_dict["QRZ"])
                        buttons_to_send.append(parent.esm_dict["HISCALL"])
                        buttons_to_send.append(parent.esm_dict["QRZ"])
                        buttons_to_send.append("LOGIT")
                    elif self.prev_call == parent.callsign.text():
                        parent.make_button_green(parent.esm_dict["QRZ"])
                        buttons_to_send.append(parent.esm_dict["QRZ"])
                        buttons_to_send.append("LOGIT")

                    if with_enter is True:
                        if self.prev_call == "":
                            self.prev_call = parent.callsign.text()
                            parent.restore_button_color(parent.esm_dict["HISCALL"])
                            parent.restore_button_color(parent.esm_dict["EXCH"])
                            parent.make_button_green(parent.esm_dict["QRZ"])

            elif parent.current_widget in ("sent", "receive"):
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
