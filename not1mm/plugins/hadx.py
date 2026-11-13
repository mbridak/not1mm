"""Hungarian DX Contest (HA-DX)

Find rules at: https://ha-dx.com/en/contest-rules

160-10m, once per band and mode.  An HA station sends a two-letter county, and
everyone else a serial number.  A Hungarian contact is worth 10 points, one on
the same continent 2 and another continent 5.  Each Hungarian county and each
DXCC/WAE country counts once per band.

Only the parts that differ from :mod:`not1mm.lib.contest` are here.
"""

from not1mm.lib.contest import ContestBase

# The counties an HA station may send.
HA_COUNTY = (
    "BA",
    "BE",
    "BN",
    "BO",
    "BP",
    "CS",
    "FE",
    "GY",
    "HB",
    "HE",
    "SZ",
    "KO",
    "NG",
    "PE",
    "SO",
    "SA",
    "TO",
    "VA",
    "VE",
    "ZA",
)

COUNTY_LIST = ", ".join(f"'{county}'" for county in HA_COUNTY)


class Contest(ContestBase):
    """Hungarian DX Contest."""

    DisplayName = "HA DX"
    CabrilloName = "HA-DX"
    Mode = "BOTH"  # CW SSB BOTH RTTY
    EXCHANGE_HINT = "# or County"
    DupeType = 3  # once per band and mode
    Bands = (1.8, 3.5, 7, 14, 21, 28)
    # The reports, our serial and their county or serial.
    FrameText = ("SNT", "SentNR", "HA County or SN")
    AccessibleNames = (
        "RST Sent",
        "",
        "Sent Number",
        "Hungarian county or Serial Number",
    )
    # Each Hungarian county and each country once per band.
    NumMults = 2
    Multiplier1Name = "NR"
    MultSqlString = "NR"
    IsMult1Per = 1
    Multiplier2Name = "CountryPrefix"
    MultSqlString2 = "CountryPrefix"
    IsMult2Per = 1
    SendsRTCScore = True

    def points(self):
        """10 points for an HA station, else 2/5 by continent."""
        parent = self.parent
        if parent.contact_is_dupe:
            return 0
        if parent.contact.get("NR", "") in HA_COUNTY:
            return 10

        my_continent = ""
        their_continent = ""

        result = parent.cty_lookup(parent.station.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            my_continent = item.get("continent", "")

        result = parent.cty_lookup(parent.contact.get("Call", ""))
        if result is not None:
            item = result.get(next(iter(result)))
            their_continent = item.get("continent", "")

        if my_continent == their_continent:
            return 2
        return 5

    def mult_value(self, slot, contact):
        """A county when the exchange is text, a country when it is a serial."""
        if slot == 1:
            county = contact.get("NR")
            return county if county in HA_COUNTY else None
        if slot == 2:
            if isinstance(contact.get("NR"), int):
                return contact.get("CountryPrefix") or None
            return None
        return super().mult_value(slot, contact)

    def mult_sql(self, slot):
        """The same keys as SQL, for counting the log."""
        if slot == 1:
            return "CASE WHEN typeof(NR) = 'text' AND Points = 10 THEN NR END"
        if slot == 2:
            return "CASE WHEN typeof(NR) = 'integer' THEN CountryPrefix END"
        return super().mult_sql(slot)

    def get_mults(self):
        """The score page's single row, as the module summed it."""
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

        The exchange is our serial *and* their county or serial, so both fields
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
