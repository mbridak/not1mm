"""RAC Canada Day Contest

Find rules at: https://www.rac.ca/canada-day-contest/

160-10m, once per band and mode.  A RAC official station is worth 20 points,
any other Canadian station 10 and a station outside Canada 2.  The multiplier
is each Canadian province or territory once per band and mode -- which is what
a Canadian station sends -- while a station elsewhere sends a serial number,
and a serial number is not a multiplier.
"""

from not1mm.lib.contest import ContestBase

RAC_OFFICIAL_STATIONS = (
    "VA2RAC",
    "VA3RAC",
    "VE1RAC",
    "VE4RAC",
    "VE5RAC",
    "VE6RAC",
    "VE7RAC",
    "VE8RAC",
    "VE9RAC",
    "VO1RAC",
    "VO2RAC",
    "VY0RAC",
    "VY1RAC",
    "VY2RAC",
    "VE3RHQ",
)


class Contest(ContestBase):
    """RAC Canada Day."""

    DisplayName = "CANADA DAY"
    CabrilloName = "CANADA-DAY"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Province/Territory"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The reports, our serial and their province/territory or serial.
    FrameText = ("SNT", "SentNR", "Prov/territory or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Province Territory or Serial Number",
    )
    # Each province/territory once per band and mode; a serial is not one.
    NumMults = 1
    Multiplier1Name = "Province/Territory"
    MultSqlString = "NR"
    IsMult1Per = 3

    def points(self):
        """20 for a RAC official station, 10 for Canada, 2 for anywhere else."""
        if self.parent.contact_is_dupe:
            return 0
        call = self.parent.contact.get("Call", "")
        if call in RAC_OFFICIAL_STATIONS:
            return 20
        result = self.parent.cty_lookup(call)
        if result is not None:
            item = result.get(next(iter(result)))
            if item.get("entity", "") == "Canada":
                return 10
        return 2

    def mult_value(self, slot, contact):
        """A province is text; a serial number is not a multiplier.

        ``NR`` is an INTEGER column, so a Canadian station's province is stored
        as text and a DX station's serial number as an integer.
        """
        if slot == 1:
            nr = contact.get("NR")
            if isinstance(nr, str) and nr and not nr.isdigit():
                return nr
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same key as SQL, for counting the log."""
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' AND NR != '' THEN NR END"
        return super().mult_sql(slot)

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["SentNr"] = parent.other_1.text()
        parent.contact["NR"] = parent.other_2.text().upper()

    def recalculate_mults(self):
        """No marks: this contest never set ``IsMultiplier1``."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The contact needs *both* exchange fields -- our serial and their
        province/territory or serial -- before it can be logged.
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
