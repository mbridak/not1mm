"""DARC Christmas Contest (XMAS)

Find rules at: https://www.darc.de/der-club/referate/conteste/weihnachtswettbewerb/regeln/
Upload logs at: https://dxhf2.darc.de/~xmaslog/upload.cgi?form=referat&lang=de

80m and 40m, once per band and mode.  The exchange is RST and a DOK, or "NM"
for a non-member in DL and a serial number from outside.  Each DOK and each
WPX prefix is a multiplier once per band and mode; "NM" and an empty prefix
are not multipliers.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """DARC Christmas Contest."""

    DisplayName = "DARC XMAS"
    CabrilloName = "XMAS"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "DOK/NM or #"
    DupeType = 3  # work each band/mode once
    SendsRTCScore = True
    PointsPerContact = 1
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Snt",
        "Rcv",
        "SentNr",
        "RcvNr",
        "M1",
        "M2",
        "PTS",
    ]
    FrameText = ("SNT", "DOK/# Sent", "DOK/# RCVD")
    AccessibleNames = ("", "", "RST Sent", "DOK/NM or Number")
    # A WPX prefix and a DOK, each once per band and mode.
    NumMults = 2
    Multiplier1Name = "WPXPrefix"
    MultSqlString = "WPXPrefix"
    IsMult1Per = 3
    Multiplier2Name = "DOK"
    MultSqlString2 = "NR"
    IsMult2Per = 3

    def mult_sql(self, slot):
        """A prefix is not a multiplier when empty; a DOK only from DL.

        A DOK counts only for a DL station, only when it is text (a serial from
        outside is not a district) and only when it is not "NM"; an empty value
        is not one either.  The module's replay said the same, and its query
        compared the stored ``NR``.
        """
        if slot == 1:
            return "NULLIF(WPXPrefix, '')"
        if slot == 2:
            return (
                "CASE WHEN CountryPrefix = 'DL' AND typeof(NR) = 'text' "
                "AND NR <> '' AND upper(NR) <> 'NM' THEN upper(NR) END"
            )
        return super().mult_sql(slot)

    def mult_value(self, slot, contact):
        """The same key as :meth:`mult_sql`, from a contact."""
        if slot == 1:
            return contact.get("WPXPrefix") or None
        if slot == 2:
            dok = contact.get("NR", "")
            if (
                contact.get("CountryPrefix") == "DL"
                and isinstance(dok, str)
                and dok
                and dok.upper() != "NM"
            ):
                return dok.upper()
            return None
        return super().mult_value(slot, contact)

    def set_contact_vars(self):
        """The received DOK, and the two multipliers it is worth."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()
        self.mark_multipliers()

    def prefill(self):
        """Fill the sent exchange, then recall the station's last DOK."""
        parent = self.parent
        super().prefill()
        if parent.other_2.text():
            return
        call = parent.callsign.text().upper()
        result = parent.database.exec_sql(
            "select NR from dxlog where Call = ? and ContestName = ? "
            "order by ts desc;",
            (call, self.CabrilloName),
        )
        if result and isinstance(result.get("NR", ""), str):
            parent.other_2.setText(str(result.get("NR", "")))

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        Both exchange fields -- the sent DOK/serial and the received one --
        are needed before the contact can be logged.
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
        """Prefill the received DOK from the call history file."""
        parent = self.parent
        result = parent.database.fetch_call_history(parent.callsign.text())
        if result:
            parent.history_info.setText(f"{result.get('UserText', '')}")
            if parent.other_2.text() == "":
                parent.other_2.setText(f"{result.get('Exch1', '')}")
