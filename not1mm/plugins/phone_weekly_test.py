"""Phone Weekly Test (Phone Fray)

Find rules at: http://www.perluma.com/Phone_Fray_Contest_Rules.pdf

160m to 15m, once per band, SSB.  A North American station scores a point for
every contact and a station elsewhere scores one only against North America.
The exchange is a name, and a North American station adds its
state/province/country; each of those sections is a multiplier once per band.
A station outside North America sends only a name and gives no multiplier.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase


class Contest(ContestBase):
    """Phone Weekly Test (Phone Fray)."""

    DisplayName = "PHONE WEEKLY TEST"
    CabrilloName = "PHONE-WEEKLY-TEST"
    Mode = "SSB"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Name or Name + SPC"
    DupeType = 2  # work each band once
    Bands = (1.8, 3.5, 7, 14, 21)
    LogInfo = [
        "YYYY-MM-DD HH:MM:SS",
        "Call",
        "Freq",
        "Name",
        "Sect",
        "M1",
        "PTS",
    ]
    # The reports are not part of this contest's exchange.
    EntryFields = ("field3", "field4")
    FrameText = ("", "Name", "State")
    AccessibleNames = ("", "", "Name", "State")
    NextField = "other_1"
    # Each US state, VE province and North American country, once per band.  A
    # station outside North America sends only a name, so it has no section --
    # the empty section used to count as one multiplier that they all shared.
    NumMults = 1
    Multiplier1Name = "Sect"
    MultSqlString = "Sect"
    IsMult1Per = 1

    def mult_sql(self, slot: int):
        """The section key, excluding the empty one and "DX"."""
        if slot != 1:
            return super().mult_sql(slot)
        return "CASE WHEN Sect NOT IN ('', 'DX') THEN Sect END"

    def mult_value(self, slot: int, contact):
        """The same section key as :meth:`mult_sql`, from a row or a spot."""
        if slot != 1:
            return super().mult_value(slot, contact)
        sect = contact.get("Sect", "")
        if sect in ("", "DX"):
            return None
        return sect

    def set_contact_vars(self):
        """The exchange, and the section multiplier."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["Name"] = parent.other_1.text().upper()
        parent.contact["Sect"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.contest_settings.get("SentExchange", 0)
        self.mark_multipliers()

    def prefill(self):
        """`other_1` is the *received* name, so the sent exchange is the setup's."""

    def points(self):
        """One point, but only when one end of the contact is in North America."""
        parent = self.parent
        if parent.contact_is_dupe > 0:
            return 0
        my_continent = ""
        his_continent = ""
        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_continent = item.get("continent", "")
        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            his_continent = item.get("continent", "")
        if my_continent == "NA" or his_continent == "NA":
            return 1
        return 0

    def recalculate_mults(self):
        """Mark the first scoring contact of each section on each band."""
        database = self.parent.database
        seen = set()
        for contact in database.fetch_all_contacts_asc():
            value = self.mult_value(1, contact)
            key = (value, contact.get("Band", ""))
            if value and contact.get("Points", 0) == 1 and key not in seen:
                contact["IsMultiplier1"] = 1
            else:
                contact["IsMultiplier1"] = 0
            if value:
                seen.add(key)
            database.change_contact(contact)
        self.after_recalculate_mults()

    def after_recalculate_mults(self):
        """Refresh the log window, as the module's replay did."""
        cmd = {}
        cmd["cmd"] = "UPDATELOG"
        if self.parent.log_window:
            self.parent.log_window.msg_from_main(cmd)

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        A North American station sends a name *and* a section, so both entry
        fields have to be filled before the contact can be finished.
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

    def cabrillo_qso_line(self, contact):
        """The Phone Fray line: the sent exchange, then the name and section."""
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
