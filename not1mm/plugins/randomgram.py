"""RandomGram plugin

Find rules at: https://n1mmwp.hamdocs.com/mmfiles/randomgram-udc/

CW only, one five-character group sent and one received, two points a contact
and no multipliers.  A station may be worked again on the same band
(``DupeType = 4``).  The next group to send is read from ``~/rg.txt`` when the
contest is loaded.

The Cabrillo export is deliberately empty -- the event wants a list of the
groups received, not a log -- so :meth:`Contest.cabrillo` stays a no-op.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

import os

from not1mm.lib.contest import ContestBase
from not1mm.lib.fields import DEFAULT_ENTRY_WINDOW

SOAPBOX_HINT = """This plugin was submitted by @alduhoo.
It reads a rg.txt file if it exists in the user’s home directory to populate the next group in the sent exchange field.
"""

rgGroupsPath = os.path.join(os.path.expanduser("~"), "rg.txt")
try:
    with open(rgGroupsPath, "r", encoding="utf-8") as groups_file:
        rgGroups = groups_file.readlines()
except (OSError, UnicodeError):
    rgGroups = []


class Contest(ContestBase):
    """RandomGram: one group sent, one received."""

    DisplayName = "RandomGram"
    CabrilloName = "RANDOMGRAM"
    Mode = "CW"
    DupeType = 4  # no dupe checking
    PointsPerContact = 2
    SOAPBOX_HINT = SOAPBOX_HINT
    EntryWindowInfo = DEFAULT_ENTRY_WINDOW
    FrameText = ("SNT", "RCV", "SentRG", "RcvRG")
    AccessibleNames = (
        "RST Sent",
        "RST Received",
        "Sent RandomGram",
        "Received RandomGram",
    )
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
    ]

    def set_contact_vars(self):
        """Copy the reports and the two groups into the contact."""
        parent = self.parent
        parent.contact["SNT"] = parent.fields.SNTText.text()
        parent.contact["RCV"] = parent.fields.RCVText.text()
        parent.contact["Comment"] = parent.fields.RcvNrText.text()
        parent.contact["SentNr"] = parent.fields.SntNrText.text()
        parent.contact["NR"] = parent.fields.RcvNrText.text()

    def prefill(self):
        """Offer the next group from ``~/rg.txt``, one per logged contact."""
        qso_count = self.show_qso()
        if len(rgGroups) <= qso_count:
            return

        # The line keeps its newline from readlines(), so strip it before it
        # goes into the exchange field.
        next_group = str(rgGroups[qso_count]).strip()
        if next_group:
            self.parent.fields.SntNrText.setText(next_group)

    def cabrillo(self, filename, file_encoding):
        """No Cabrillo export: the event wants a list of groups, not a log."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        There is no exchange to repeat, so the contact is logged as soon as an
        exchange field has focus; the base's machine would ask for a repeat.
        """
        parent = self.parent
        if new_focused_widget is not None:
            parent.current_widget_object = new_focused_widget
        focused = getattr(parent, "current_widget_object", None)

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
            if focused is parent.callsign:
                if len(parent.callsign.text()) < 3:
                    parent.make_button_green(parent.esm_dict["CQ"])
                    buttons_to_send.append(parent.esm_dict["CQ"])
                elif len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["HISCALL"])
                    parent.make_button_green(parent.esm_dict["EXCH"])
                    buttons_to_send.append(parent.esm_dict["HISCALL"])
                    buttons_to_send.append(parent.esm_dict["EXCH"])

            elif focused in (parent.fields.SntNrText, parent.fields.RcvNrText):
                buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)
        else:
            if focused is parent.callsign:
                if len(parent.callsign.text()) > 2:
                    parent.make_button_green(parent.esm_dict["MYCALL"])
                    buttons_to_send.append(parent.esm_dict["MYCALL"])

            elif focused in (parent.fields.SntNrText, parent.fields.RcvNrText):
                buttons_to_send.append("LOGIT")

            if with_enter is True and bool(len(buttons_to_send)):
                for button in buttons_to_send:
                    if button:
                        if button == "LOGIT":
                            parent.save_contact()
                            continue
                        parent.process_function_key(button)

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
            if parent.fields.SntNrText.text() == "":
                parent.fields.SntNrText.setText(f"{result.get('Name', '')}")
