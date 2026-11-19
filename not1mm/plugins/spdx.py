"""SP DX Contest

Find rules at: https://spdxcontest.pzk.org.pl/2026/rules.php

80-10m, once per band and mode.  A Polish station sends a one-letter province
and everyone else a serial number.  A Polish station scores 3 points for a DX
contact, 1 inside Europe and nothing between two Polish stations; a foreign
station scores 3 for a Polish contact and nothing else.  A Polish station
counts the DXCC countries it worked (Poland itself excepted) and a foreign
station the Polish provinces, each once per band regardless of mode.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# The one-letter provinces a Polish station may send.
POLISH_PROVINCES = (
    "B",
    "C",
    "D",
    "F",
    "G",
    "J",
    "K",
    "L",
    "M",
    "O",
    "P",
    "R",
    "S",
    "U",
    "W",
    "Z",
)

PROVINCE_LIST = ", ".join(f"'{province}'" for province in POLISH_PROVINCES)


class Contest(ContestBase):
    """SP DX Contest."""

    DisplayName = "SPDX"
    CabrilloName = "SPDX"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "Province or #"
    DupeType = 3  # once per band and mode
    Bands = (3.5, 7, 14, 21, 28)
    # The reports, our province or serial and theirs.
    FrameText = ("SNT", "SentNR", "Prov or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Province or Serial Number",
    )
    # The country for a Polish entrant, the provinces for everyone else.
    NumMults = 1
    Multiplier1Name = "CountryPrefix"
    MultSqlString = "CountryPrefix"
    IsMult1Per = 1
    SendsRTCScore = True

    def _is_sp(self) -> bool:
        """True when the entrant is a Polish station."""
        result = self.parent.cty_lookup(self.parent.station.get("Call", ""))
        if not result:
            return False
        item = result.get(next(iter(result)), {})
        return item.get("entity", "") == "Poland"

    def points(self):
        """The Polish/foreign ladder; a non-Polish to non-Polish QSO is nothing."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0

        my_country = ""
        their_country = ""
        their_continent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_country = item.get("entity", "")

        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            their_country = item.get("entity", "")
            their_continent = item.get("continent", "")

        if my_country == "Poland":
            if their_country == "Poland":
                return 0
            if their_continent == "EU":
                return 1
            return 3
        if their_country == "Poland":
            return 3
        return 0

    def mult_value(self, slot, contact):
        """The country for a Polish entrant, the province for everyone else."""
        if slot == 1:
            if self._is_sp():
                country = contact.get("CountryPrefix")
                return country if country not in (None, "", "SP") else None
            province = contact.get("NR")
            return province if province in POLISH_PROVINCES else None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same side-dependent key as SQL, for counting the log."""
        if slot == 1:
            if self._is_sp():
                return (
                    "CASE WHEN CountryPrefix != '' AND CountryPrefix != 'SP' "
                    "THEN CountryPrefix END"
                )
            return f"CASE WHEN NR IN ({PROVINCE_LIST}) THEN NR END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's single row, as the module reported it."""
        return {"state": self.show_mults()}

    def set_contact_vars(self):
        """The reports and the exchange; this contest marks no multipliers."""
        parent = self.parent
        parent.contact["SNT"] = parent.sent.text()
        parent.contact["RCV"] = parent.receive.text()
        parent.contact["NR"] = parent.other_2.text().upper()
        parent.contact["SentNr"] = parent.other_1.text()

    def recalculate_mults(self):
        """Nothing to mark: the count comes from the log, not the M column."""

    def process_esm(self, new_focused_widget=None, with_enter=False):
        """ESM state machine.

        The exchange is our province or serial *and* theirs, so both fields
        have to be filled before the contact is finished.
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
